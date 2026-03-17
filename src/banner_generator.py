"""
banner_generator.py
~~~~~~~~~~~~~~~~~~~
Генерация баннеров в двух форматах:
  • JPEG-превью  — через Pillow (RGB, быстро, для Telegram)
  • PDF для печати — через ReportLab (промежуточный) + Ghostscript (финальный):
      - PDF/A-1b совместимый
      - CMYK с ICC-профилем ISOcoated_v2_300
      - Все шрифты переведены в кривые (outlines)

Двухшаговая схема:
    ReportLab → tmp_raw.pdf → Ghostscript → print_ready.pdf → BytesIO

Решение UnsupportedDeviceColorSpace:
    OutputIntent с ICC-профилем встраивается на этапе ReportLab через
    прямую инъекцию в PDFCatalog (_catalog.__NoDefault__ + PDFArray).
    ReportLab не поддерживает OutputIntents нативно, но PDFCatalog.format()
    читает все атрибуты через getattr — достаточно добавить атрибут и
    зарегистрировать его в __NoDefault__ / __Refs__ на экземпляре.
    Ghostscript получает raw.pdf уже с OutputIntent и сохраняет его при
    PDF/A-1b конвертации без конфликта цветовых пространств.
"""

import io
import logging
import os
import subprocess
import tempfile

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfdoc, pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from .config import COLORS, FONTS, ICC_PROFILE_PATH, SAFE_ZONE_MM

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Регистрация шрифтов в ReportLab (при импорте модуля)
# ---------------------------------------------------------------------------
_fonts_registered = False


def _ensure_fonts_registered() -> None:
    global _fonts_registered
    if _fonts_registered:
        return
    missing = []
    for name, path in FONTS.items():
        if not os.path.exists(path):
            missing.append(f"{name} → {path}")
            continue
        try:
            pdfmetrics.registerFont(TTFont(name, path))
        except Exception as exc:
            logger.error("Не удалось зарегистрировать шрифт %s: %s", name, exc)
            raise RuntimeError(
                f"Ошибка загрузки шрифта '{name}' из '{path}': {exc}\n"
                "Убедитесь, что файлы шрифтов находятся в папке fonts/"
            ) from exc
    if missing:
        raise FileNotFoundError(
            "Отсутствуют файлы шрифтов:\n" + "\n".join(missing)
        )
    _fonts_registered = True


# ---------------------------------------------------------------------------
# Внутренняя функция: расчёт раскладки текста
# ---------------------------------------------------------------------------
def _calculate_layout(
    text_items: list[dict],
    safe_width: float,
    safe_height: float,
    line_spacing_ratio: float = 1.2,
    measure_fn=None,
) -> list[dict]:
    """
    Рассчитывает финальные размеры шрифта для каждой строки с учётом:
      - индивидуального масштаба строки (scale)
      - ограничения по высоте (вертикальный fit)

    measure_fn(text, size) → (width, height)
    """
    details = []
    for item in text_items:
        line = item.get("text", "").strip()
        scale_modifier = item.get("scale", 1.0)
        if not line:
            continue
        effective_width = safe_width * scale_modifier

        ref_size = 100.0
        ref_w, ref_h = measure_fn(line, ref_size)
        if ref_w == 0:
            continue

        font_size = ref_size * (effective_width / ref_w)
        _, line_h = measure_fn(line, font_size)
        details.append(
            {
                "text": line,
                "font_size": font_size,
                "height": line_h,
            }
        )

    # Вертикальный fit: если не влезает — масштабируем все строки
    total_h = sum(d["height"] * line_spacing_ratio for d in details)
    if total_h > safe_height and total_h > 0:
        fit = safe_height / total_h
        for d in details:
            d["font_size"] *= fit
            d["height"] *= fit

    return details


# ---------------------------------------------------------------------------
# JPEG-превью (Pillow, RGB)
# ---------------------------------------------------------------------------
def create_preview_jpeg(data: dict) -> io.BytesIO:
    width_mm: int = data["width"]
    height_mm: int = data["height"]
    bg_color_name: str = data["bg_color"]
    text_color_name: str = data["text_color"]
    text_items: list[dict] = data["text_lines"]
    font_name: str = data["font"]

    _ensure_fonts_registered()

    # Масштаб: 1 пиксель = 1 мм (достаточно для превью в Telegram)
    scale = 1.0
    w_px = int(width_mm * scale)
    h_px = int(height_mm * scale)
    safe_px = SAFE_ZONE_MM * scale

    bg_rgb = COLORS[bg_color_name]["rgb"]
    text_rgb = COLORS[text_color_name]["rgb"]
    font_path = FONTS[font_name]

    image = Image.new("RGB", (w_px, h_px), bg_rgb)
    draw = ImageDraw.Draw(image)

    safe_w = w_px - 2 * safe_px
    safe_h = h_px - 2 * safe_px

    def pillow_measure(text: str, size: float):
        fnt = ImageFont.truetype(font_path, int(size))
        bbox = draw.textbbox((0, 0), text, font=fnt)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]

    details = _calculate_layout(text_items, safe_w, safe_h, measure_fn=pillow_measure)

    # Вертикальное центрирование
    total_h = sum(d["height"] * 1.2 for d in details)
    y = safe_px + (safe_h - total_h) / 2

    for d in details:
        fnt = ImageFont.truetype(font_path, int(d["font_size"]))
        bbox = draw.textbbox((0, 0), d["text"], font=fnt)
        text_w = bbox[2] - bbox[0]
        x = safe_px + (safe_w - text_w) / 2
        # Компенсируем bbox[0] и bbox[1] — offset глифа относительно origin.
        # Без этого каждая строка рисуется на bbox[1] пикселей ниже расчётной
        # позиции, что при нескольких строках накапливается в заметный сдвиг.
        draw.text((x - bbox[0], y - bbox[1]), d["text"], font=fnt, fill=text_rgb)
        y += d["height"] * 1.2

    # --- Вотермарка ---
    # Текст поверх JPEG-превью. PDF платный — вотермарка мотивирует к покупке.
    # Размер: ~4% от меньшей стороны (читаемо, но не перекрывает контент).
    wm_text = "Сделано в @BannerPrintBot"
    wm_size = max(12, int(min(w_px, h_px) * 0.04))
    try:
        # Пробуем системный шрифт; если нет — деградируем до default
        wm_font = ImageFont.truetype("fonts/GolosText-Regular.ttf", wm_size)
    except (OSError, IOError):
        wm_font = ImageFont.load_default()

    wm_bbox = draw.textbbox((0, 0), wm_text, font=wm_font)
    wm_w = wm_bbox[2] - wm_bbox[0]
    wm_h = wm_bbox[3] - wm_bbox[1]

    # Позиция: правый нижний угол с отступом safe_px / 2
    margin = int(safe_px / 2)
    wm_x = w_px - wm_w - margin - wm_bbox[0]
    wm_y = h_px - wm_h - margin - wm_bbox[1]

    # Полупрозрачная подложка для читаемости на любом фоне.
    # Pillow RGBA composite: рисуем overlay отдельно, накладываем на RGB.
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    ov_draw = ImageDraw.Draw(overlay)

    pad = 6
    ov_draw.rectangle(
        [wm_x - pad, wm_y - pad, wm_x + wm_w + pad, wm_y + wm_h + pad],
        fill=(0, 0, 0, 120),
    )
    ov_draw.text((wm_x, wm_y), wm_text, font=wm_font, fill=(255, 255, 255, 220))

    image = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")

    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=90)
    buf.seek(0)
    return buf


# ---------------------------------------------------------------------------
# Встраивание OutputIntent в PDF через инъекцию в PDFCatalog
# ---------------------------------------------------------------------------
def _embed_output_intent(c: canvas.Canvas, icc_path: str) -> None:
    """
    Встраивает OutputIntent с ICC-профилем в PDF через прямую инъекцию
    в PDFCatalog экземпляра ReportLab Canvas.

    ReportLab не поддерживает OutputIntents нативно. PDFCatalog.format()
    собирает словарь через getattr по спискам __Defaults__, __NoDefault__
    и __Refs__. Добавляем 'OutputIntents' в эти списки на экземпляре
    каталога (не на классе — не затрагиваем другие PDF) и задаём атрибут
    с PDFArray из одного объекта OutputIntent.

    Структура согласно ISO 19005-1, секция 6.2.2:
        Catalog.OutputIntents → array → OutputIntent dict → DestOutputProfile stream
    """
    try:
        with open(icc_path, "rb") as f:
            icc_data = f.read()
    except OSError as exc:
        logger.warning("Не удалось прочитать ICC-профиль: %s", exc)
        return

    doc = c._doc

    # ICC stream: N=4 (CMYK), Alternate=/DeviceCMYK
    # Используем ZCompress=False: некоторые версии GS некорректно читают
    # сжатый ICC stream внутри PDF/A при конвертации
    icc_dict = pdfdoc.PDFDictionary({"N": 4, "Alternate": "/DeviceCMYK"})
    icc_stream = pdfdoc.PDFStream(
        dictionary=icc_dict,
        content=icc_data,
        filters=None,  # без сжатия — максимальная совместимость с GS
    )
    icc_ref = doc.Reference(icc_stream)

    # OutputIntent объект
    oi_dict = pdfdoc.PDFDictionary({
        "Type": "/OutputIntent",
        "S": "/GTS_PDFA1",
        "OutputConditionIdentifier": pdfdoc.PDFString("ISOcoated_v2_300_eci"),
        "Info": pdfdoc.PDFString("ISOcoated v2 300% (ECI)"),
        "DestOutputProfile": icc_ref,
    })
    oi_ref = doc.Reference(oi_dict)

    # Инъекция в каталог: добавляем в списки на экземпляре, не на классе
    cat = doc._catalog
    cat.__NoDefault__ = list(cat.__NoDefault__) + ["OutputIntents"]
    cat.__Refs__ = list(cat.__Refs__) + ["OutputIntents"]
    cat.OutputIntents = pdfdoc.PDFArray([oi_ref])

    logger.debug("OutputIntent встроен: %s", icc_path)


# ---------------------------------------------------------------------------
# Шаг 1: промежуточный PDF через ReportLab (DeviceCMYK + OutputIntent)
# ---------------------------------------------------------------------------
def _create_raw_pdf(data: dict) -> io.BytesIO:
    width_mm: int = data["width"]
    height_mm: int = data["height"]
    bg_color_name: str = data["bg_color"]
    text_color_name: str = data["text_color"]
    text_items: list[dict] = data["text_lines"]
    font_name: str = data["font"]

    _ensure_fonts_registered()

    font_path = FONTS[font_name]
    w_pt = width_mm * mm
    h_pt = height_mm * mm

    # Layout ведётся в мм (= px при scale=1) — идентично create_preview_jpeg.
    # Это гарантирует одинаковый font_size и вертикальный fit в обоих форматах.
    # После layout font_size и height переводятся в pt для ReportLab.
    safe_w_mm = float(width_mm - 2 * SAFE_ZONE_MM)
    safe_h_mm = float(height_mm - 2 * SAFE_ZONE_MM)

    buf = io.BytesIO()
    # PDF 1.4 обязателен для PDF/A-1b (GS 10.x отвергает 1.3 с политикой =1)
    c = canvas.Canvas(buf, pagesize=(w_pt, h_pt), pdfVersion=(1, 4))

    # --- Фон ---
    bg_cmyk = COLORS[bg_color_name]["cmyk"]
    if bg_color_name == "Белый":
        # Белый фон: тонкая рамка для обозначения края (типографская метка)
        c.setStrokeColorCMYK(0, 0, 0, 0.3)
        c.setLineWidth(0.1)
        c.rect(0, 0, w_pt, h_pt, fill=0, stroke=1)
    else:
        c_v, m_v, y_v, k_v = [x / 100 for x in bg_cmyk]
        c.setFillColorCMYK(c_v, m_v, y_v, k_v)
        c.rect(0, 0, w_pt, h_pt, fill=1, stroke=0)

    # --- Текст ---
    txt_cmyk = COLORS[text_color_name]["cmyk"]
    tc, tm, ty, tk = [x / 100 for x in txt_cmyk]
    c.setFillColorCMYK(tc, tm, ty, tk)

    def rl_measure(text: str, size: float):
        # size — в мм (единицы layout). stringWidth требует pt.
        size_pt = size * mm
        # Ширина в pt → мм, чтобы совпадало с safe_w_mm.
        w_mm = pdfmetrics.stringWidth(text, font_name, size_pt) / mm
        # Высота — через Pillow textbbox (px = мм при scale=1).
        # face.ascent / 1000 * size_pt (~0.85×size_pt) завышает высоту
        # относительно реального bbox (~0.65×size), что вызывает
        # преждевременный вертикальный fit и уменьшает шрифт в PDF.
        # Pillow даёт точный визуальный bbox — layout идентичен превью.
        _fnt = ImageFont.truetype(font_path, int(size))
        _bbox = ImageDraw.Draw(Image.new("RGB", (1, 1))).textbbox((0, 0), text, font=_fnt)
        h_mm = _bbox[3] - _bbox[1]
        return w_mm, h_mm

    details = _calculate_layout(text_items, safe_w_mm, safe_h_mm, measure_fn=rl_measure)

    # font_size и height из layout в мм → переводим в pt для ReportLab.
    for d in details:
        d["font_size_pt"] = d["font_size"] * mm
        d["height_pt"] = d["height"] * mm

    # Вертикальное центрирование внутри safe zone — зеркало Pillow:
    #   Pillow:     y      = safe_px  + (safe_h  - total_h)  / 2   (от верха вниз)
    #   ReportLab:  y_cursor = h_pt - safe_top - (safe_h_pt - total_h_pt) / 2
    # y_cursor = верхняя граница блока текста (от неё baseline = y_cursor - height).
    total_h_pt = sum(d["height_pt"] * 1.2 for d in details)
    safe_pt = SAFE_ZONE_MM * mm          # отступ safe zone в pt (все стороны)
    safe_h_pt = safe_h_mm * mm
    y_cursor = h_pt - safe_pt - (safe_h_pt - total_h_pt) / 2

    for d in details:
        size_pt = d["font_size_pt"]
        text_w = pdfmetrics.stringWidth(d["text"], font_name, size_pt)
        x = safe_pt + (safe_w_mm * mm - text_w) / 2
        y_pos = y_cursor - d["height_pt"]

        c.setFont(font_name, size_pt)
        to = c.beginText(x, y_pos)
        to.setFont(font_name, size_pt)
        to.textLine(d["text"])
        c.drawText(to)

        y_cursor -= d["height_pt"] * 1.2

    # --- OutputIntent: встраиваем ICC-профиль до c.save() ---
    # Это ключевое исправление: GS получает PDF уже с OutputIntent
    # и сохраняет его при PDF/A-1b конвертации без конфликта цветовых пространств
    if os.path.exists(ICC_PROFILE_PATH):
        _embed_output_intent(c, ICC_PROFILE_PATH)
    else:
        logger.warning(
            "ICC-профиль не найден: %s — OutputIntent не будет встроен в raw PDF",
            ICC_PROFILE_PATH,
        )

    c.showPage()
    c.save()
    buf.seek(0)
    return buf


# ---------------------------------------------------------------------------
# Шаг 2: постобработка через Ghostscript → PDF/A-1b
#
# PDF/A-1b выбран намеренно (не 1a):
#   - 1a требует Tagged PDF (MarkInfo) — избыточно для печатной графики
#   - 1b требует только встроенные шрифты/профиль — принимают все типографии
#
# -dNOSAFER обязателен: без него GS 10.x блокирует чтение любых файлов
# вне cwd (включая ICC-профили) — Permission denied. Контейнер изолирован,
# сетевого доступа нет, sandbox GS не нужен.
# ---------------------------------------------------------------------------
def _ghostscript_process(input_path: str, output_path: str) -> None:
    icc_exists = os.path.exists(ICC_PROFILE_PATH)

    if not icc_exists:
        logger.warning(
            "ICC-профиль не найден: %s — PDF будет без OutputIntent",
            ICC_PROFILE_PATH,
        )

    cmd = [
        "gs",
        "-dBATCH",
        "-dNOPAUSE",
        "-dNOSAFER",   # нужен для чтения ICC-профилей с диска в GS 10.x sandbox
        "-sDEVICE=pdfwrite",

        # PDF/A-1b
        "-dPDFA=1",
        # Policy=2: при несовместимости GS исправляет и продолжает (не падает).
        # Policy=1 вызывает fatal exit при любом предупреждении — слишком жёстко
        # для PDF от ReportLab, который может иметь незначительные отклонения.
        "-dPDFACompatibilityPolicy=2",

        "-dCompatibilityLevel=1.4",
        "-dPDFSETTINGS=/prepress",

        # Шрифты → кривые
        "-dNoOutputFonts",

        # CMYK: конвертируем всё включая изображения
        "-sColorConversionStrategy=CMYK",
        "-sColorConversionStrategyForImages=CMYK",
        "-dProcessColorModel=/DeviceCMYK",
    ]

    if icc_exists:
        cmd += [
            f"-sOutputICCProfile={ICC_PROFILE_PATH}",
            f"-sDefaultCMYKProfile={ICC_PROFILE_PATH}",
        ]

    cmd += [
        f"-sOutputFile={output_path}",
        input_path,
    ]

    logger.info("Запуск Ghostscript: %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.stdout:
        logger.info("Ghostscript stdout:\n%s", result.stdout)
    if result.stderr:
        logger.info("Ghostscript stderr:\n%s", result.stderr)

    if result.returncode != 0:
        raise RuntimeError(
            f"Ghostscript завершился с ошибкой "
            f"(код {result.returncode}):\n{result.stderr}"
        )

    logger.info("Ghostscript завершён успешно → %s", output_path)


# ---------------------------------------------------------------------------
# Публичная функция: финальный PDF для типографии
# ---------------------------------------------------------------------------
def create_final_pdf(data: dict) -> io.BytesIO:
    """
    Возвращает BytesIO с PDF-файлом, готовым для передачи в типографию:
      - CMYK с ICC-профилем ISOcoated_v2_300
      - Шрифты переведены в кривые
      - PDF/A-1b совместимый формат
    """
    # Шаг 1: промежуточный PDF (с OutputIntent внутри)
    raw_buf = _create_raw_pdf(data)

    # Шаг 2: Ghostscript постобработка
    with tempfile.TemporaryDirectory() as tmpdir:
        raw_path = os.path.join(tmpdir, "raw.pdf")
        out_path = os.path.join(tmpdir, "print_ready.pdf")

        with open(raw_path, "wb") as f:
            f.write(raw_buf.getbuffer())

        _ghostscript_process(raw_path, out_path)

        with open(out_path, "rb") as f:
            result_buf = io.BytesIO(f.read())

    result_buf.seek(0)
    return result_buf


# ---------------------------------------------------------------------------
# Превью шрифтов для выбора в боте
# ---------------------------------------------------------------------------
def create_font_preview_image() -> io.BytesIO:
    font_items = list(FONTS.items())
    img_w = 1200
    line_h = 100
    padding = 50
    img_h = len(font_items) * line_h + 2 * padding

    bg_color = (240, 240, 240)
    name_color = (0, 0, 0)
    example_color = (80, 80, 80)
    example_text = "Продажа 123-45-67"
    font_size = 40

    image = Image.new("RGB", (img_w, img_h), bg_color)
    draw = ImageDraw.Draw(image)

    y = padding
    for name, path in font_items:
        if not os.path.exists(path):
            logger.warning("Шрифт для превью не найден: %s", path)
            y += line_h
            continue
        try:
            fnt = ImageFont.truetype(path, font_size)
            bbox = draw.textbbox((0, 0), name, font=fnt)
            text_y = y + (line_h - (bbox[3] - bbox[1])) / 2
            draw.text((padding, text_y), name, font=fnt, fill=name_color)

            ex_bbox = draw.textbbox((0, 0), example_text, font=fnt)
            ex_x = img_w - padding - (ex_bbox[2] - ex_bbox[0])
            draw.text((ex_x, text_y), example_text, font=fnt, fill=example_color)
        except Exception as exc:
            logger.warning("Ошибка отрисовки шрифта %s: %s", name, exc)
        y += line_h

    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=95)
    buf.seek(0)
    return buf
