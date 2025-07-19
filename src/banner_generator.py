import io
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.colors import CMYKColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from .config import SAFE_ZONE_MM, COLORS, FONTS

for name, path in FONTS.items():
    pdfmetrics.registerFont(TTFont(name, path))

def create_preview_jpeg(data):
    """Создает JPEG превью, масштабируя каждую строку НЕЗАВИСИМО."""
    width_mm, height_mm = data['width'], data['height']
    bg_color_name, text_color_name = data['bg_color'], data['text_color']
    text_lines, font_name = data['text_lines'], data['font']

    scale = 1.0
    width_px, height_px = int(width_mm * scale), int(height_mm * scale)

    bg_color_rgb = COLORS[bg_color_name]['rgb']
    text_color_rgb = COLORS[text_color_name]['rgb']
    font_path = FONTS[font_name]

    image = Image.new("RGB", (width_px, height_px), bg_color_rgb)
    draw = ImageDraw.Draw(image)

    safe_zone_px = SAFE_ZONE_MM * scale
    safe_width = width_px - 2 * safe_zone_px
    
    # --- ИЗМЕНЕНИЕ: Расчет высоты и позиционирования ---
    # Мы сначала рассчитаем все размеры, а потом будем рисовать
    line_details = []
    total_text_height = 0
    line_spacing_ratio = 1.2

    for line in text_lines:
        if not line.strip(): continue

        # 1. Рассчитываем оптимальный размер для КАЖДОЙ строки по ширине
        ref_size = 100
        ref_font = ImageFont.truetype(font_path, ref_size)
        ref_bbox = draw.textbbox((0, 0), line, font=ref_font)
        ref_width = ref_bbox[2] - ref_bbox[0]

        if ref_width == 0: continue
        
        font_size = int(ref_size * (safe_width / ref_width))
        font = ImageFont.truetype(font_path, font_size)
        
        # 2. Измеряем высоту этой строки с новым шрифтом
        line_bbox = draw.textbbox((0, 0), line, font=font)
        line_height = line_bbox[3] - line_bbox[1]
        line_width = line_bbox[2] - line_bbox[0]

        line_details.append({
            'text': line, 'font': font, 'width': line_width, 'height': line_height
        })
        total_text_height += line_height * line_spacing_ratio

    # 3. Центрируем блок текста по вертикали
    y = (height_px - total_text_height) / 2

    # 4. Рисуем каждую строку с ее собственным, индивидуально рассчитанным шрифтом
    for detail in line_details:
        # Центрируем строку внутри безопасной зоны
        x = safe_zone_px + (safe_width - detail['width']) / 2
        draw.text((x, y), detail['text'], font=detail['font'], fill=text_color_rgb)
        y += detail['height'] * line_spacing_ratio

    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='JPEG', quality=90)
    img_byte_arr.seek(0)
    return img_byte_arr


def create_final_pdf(data):
    """Создает PDF, масштабируя каждую строку НЕЗАВИСИМО."""
    width_mm, height_mm = data['width'], data['height']
    bg_color_name, text_color_name = data['bg_color'], data['text_color']
    text_lines, font_name = data['text_lines'], data['font']

    c_bg, m_bg, y_bg, k_bg = COLORS[bg_color_name]['cmyk']
    bg_color_cmyk = CMYKColor(c_bg/100, m_bg/100, y_bg/100, k_bg/100)
    
    c_text, m_text, y_text, k_text = COLORS[text_color_name]['cmyk']
    text_color_cmyk = CMYKColor(c_text/100, m_text/100, y_text/100, k_text/100)
    
    pdf_buffer = io.BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=(width_mm * mm, height_mm * mm))

    c.setFillColor(bg_color_cmyk)
    c.rect(0, 0, width_mm * mm, height_mm * mm, fill=1, stroke=0)
    
    c.setFillColor(text_color_cmyk)

    safe_width = (width_mm - 2 * SAFE_ZONE_MM) * mm

    # --- ИЗМЕНЕНИЕ: Аналогичная логика для PDF ---
    line_details_pdf = []
    total_text_height_pdf = 0
    line_spacing_ratio = 1.2
    
    for line in text_lines:
        if not line.strip(): continue

        ref_size = 100
        ref_width = pdfmetrics.stringWidth(line, font_name, ref_size)
        if ref_width == 0: continue
        
        font_size = ref_size * (safe_width / ref_width)
        
        face = pdfmetrics.getFont(font_name).face
        line_height = (face.ascent - face.descent) / 1000 * font_size
        line_width = pdfmetrics.stringWidth(line, font_name, font_size)

        line_details_pdf.append({
            'text': line, 'font_size': font_size, 'width': line_width, 'height': line_height
        })
        total_text_height_pdf += line_height * line_spacing_ratio
    
    y_start = (height_mm * mm + total_text_height_pdf) / 2
    
    for detail in line_details_pdf:
        c.setFont(font_name, detail['font_size'])
        face = pdfmetrics.getFont(font_name).face
        # Корректируем y для каждой строки, так как reportlab рисует от базовой линии
        y_pos = y_start - (face.ascent / 1000 * detail['font_size'])
        
        x_start = (SAFE_ZONE_MM * mm) + (safe_width - detail['width']) / 2
        
        text_object = c.beginText()
        text_object.setTextOrigin(x_start, y_pos)
        text_object.setFont(font_name, detail['font_size'])
        text_object.textLine(detail['text'])
        c.drawText(text_object)

        y_start -= detail['height'] * line_spacing_ratio

    c.showPage()
    c.save()
    
    pdf_buffer.seek(0)
    return pdf_buffer


def create_font_preview_image():
    font_items = list(FONTS.items())
    img_width, line_height, padding = 800, 80, 40
    img_height = len(font_items) * line_height + 2 * padding
    image = Image.new("RGB", (img_width, img_height), (240, 240, 240))
    draw = ImageDraw.Draw(image)
    y = padding
    for name, path in font_items:
        try:
            font = ImageFont.truetype(path, 40)
            bbox = draw.textbbox((0,0), name, font=font)
            text_y = y + (line_height - (bbox[3] - bbox[1])) / 2
            draw.text((padding, text_y), name, font=font, fill=(0, 0, 0))
            y += line_height
        except Exception as e:
            print(f"Не удалось загрузить шрифт {name}: {e}")
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='JPEG', quality=95)
    img_byte_arr.seek(0)
    return img_byte_arr
