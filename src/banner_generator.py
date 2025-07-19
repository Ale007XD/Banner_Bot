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

# ... (функции _calculate_font_size_proportional и create_preview_jpeg остаются без изменений) ...

def create_preview_jpeg(data):
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
    safe_height = height_px - 2 * safe_zone_px
    
    line_spacing_ratio = 1.2
    initial_details = []
    initial_total_height = 0

    for line in text_lines:
        if not line.strip(): continue
        ref_size = 100
        ref_font = ImageFont.truetype(font_path, ref_size)
        ref_bbox = draw.textbbox((0, 0), line, font=ref_font)
        ref_width = ref_bbox[2] - ref_bbox[0]
        if ref_width == 0: continue
        
        font_size = ref_size * (safe_width / ref_width)
        font = ImageFont.truetype(font_path, int(font_size))
        line_bbox = draw.textbbox((0, 0), line, font=font)
        line_height = line_bbox[3] - line_bbox[1]
        
        initial_details.append({'text': line, 'font_size': font_size, 'height': line_height})
        initial_total_height += line_height * line_spacing_ratio

    if initial_total_height == 0:
        img_byte_arr_empty = io.BytesIO()
        image.save(img_byte_arr_empty, format='JPEG', quality=90)
        img_byte_arr_empty.seek(0)
        return img_byte_arr_empty

    height_scale_factor = safe_height / initial_total_height
    final_total_height = initial_total_height * height_scale_factor
    y = (height_px - final_total_height) / 2

    for detail in initial_details:
        final_font_size = int(detail['font_size'] * height_scale_factor)
        final_font = ImageFont.truetype(font_path, final_font_size)
        
        final_bbox = draw.textbbox((0, 0), detail['text'], font=final_font)
        final_width = final_bbox[2] - final_bbox[0]
        final_height = final_bbox[3] - final_bbox[1]
        
        x = safe_zone_px + (safe_width - final_width) / 2
        draw.text((x, y), detail['text'], font=final_font, fill=text_color_rgb)
        y += final_height * line_spacing_ratio

    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='JPEG', quality=90)
    img_byte_arr.seek(0)
    return img_byte_arr


def create_final_pdf(data):
    """Создает PDF, добавляя тонкую рамку для белого фона."""
    width_mm, height_mm = data['width'], data['height']
    bg_color_name, text_color_name = data['bg_color'], data['text_color']
    text_lines, font_name = data['text_lines'], data['font']

    pdf_buffer = io.BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=(width_mm * mm, height_mm * mm))

    # --- ИЗМЕНЕНИЕ ЗДЕСЬ: Логика отрисовки фона ---
    if bg_color_name == 'Белый':
        # Для белого фона рисуем только сверхтонкую серую рамку (абрис)
        border_color = CMYKColor(0, 0, 0, 0.30) # CMYK 0,0,0,30
        c.setStrokeColor(border_color)
        c.setLineWidth(0.1)  # 0.1 пункта - стандартная толщина "hairline"
        # Рисуем прямоугольник: fill=0 (без заливки), stroke=1 (с обводкой)
        c.rect(0, 0, width_mm * mm, height_mm * mm, fill=0, stroke=1)
    else:
        # Для всех остальных цветов рисуем залитый прямоугольник без обводки
        c_bg, m_bg, y_bg, k_bg = COLORS[bg_color_name]['cmyk']
        bg_color_cmyk = CMYKColor(c_bg/100, m_bg/100, y_bg/100, k_bg/100)
        c.setFillColor(bg_color_cmyk)
        c.rect(0, 0, width_mm * mm, height_mm * mm, fill=1, stroke=0)

    # --- Логика отрисовки текста остается без изменений ---
    c_text, m_text, y_text, k_text = COLORS[text_color_name]['cmyk']
    text_color_cmyk = CMYKColor(c_text/100, m_text/100, y_text/100, k_text/100)
    c.setFillColor(text_color_cmyk)

    safe_width = (width_mm - 2 * SAFE_ZONE_MM) * mm
    safe_height = (height_mm - 2 * SAFE_ZONE_MM) * mm
    line_spacing_ratio = 1.2
    initial_details_pdf = []
    initial_total_height_pdf = 0

    for line in text_lines:
        if not line.strip(): continue
        ref_size = 100
        ref_width = pdfmetrics.stringWidth(line, font_name, ref_size)
        if ref_width == 0: continue
        font_size = ref_size * (safe_width / ref_width)
        face = pdfmetrics.getFont(font_name).face
        line_height = (face.ascent - face.descent) / 1000 * font_size
        initial_details_pdf.append({'text': line, 'font_size': font_size, 'height': line_height})
        initial_total_height_pdf += line_height * line_spacing_ratio

    if initial_total_height_pdf == 0:
        c.showPage()
        c.save()
        pdf_buffer.seek(0)
        return pdf_buffer
        
    height_scale_factor_pdf = safe_height / initial_total_height_pdf
    final_total_height_pdf = initial_total_height_pdf * height_scale_factor_pdf
    y_start = (height_mm * mm + final_total_height_pdf) / 2

    for detail in initial_details_pdf:
        final_font_size = detail['font_size'] * height_scale_factor_pdf
        final_line_height = detail['height'] * height_scale_factor_pdf
        
        c.setFont(font_name, final_font_size)
        face = pdfmetrics.getFont(font_name).face
        y_pos = y_start - (face.ascent / 1000 * final_font_size)
        
        final_width = pdfmetrics.stringWidth(detail['text'], font_name, final_font_size)
        x_start = (SAFE_ZONE_MM * mm) + (safe_width - final_width) / 2
        
        text_object = c.beginText()
        text_object.setTextOrigin(x_start, y_pos)
        text_object.setFont(font_name, final_font_size)
        text_object.textLine(detail['text'])
        c.drawText(text_object)
        
        y_start -= final_line_height * line_spacing_ratio

    c.showPage()
    c.save()
    pdf_buffer.seek(0)
    return pdf_buffer


def create_font_preview_image():
    # ... (эта функция остается без изменений) ...
    font_items = list(FONTS.items())
    img_width, line_height, padding = 1200, 100, 50
    img_height = len(font_items) * line_height + 2 * padding
    bg_color, font_name_color, example_color = (240, 240, 240), (0, 0, 0), (80, 80, 80)
    image = Image.new("RGB", (img_width, img_height), bg_color)
    draw = ImageDraw.Draw(image)
    
    y = padding
    example_text = "Продажа 123-45-67"
    font_size = 40

    for name, path in font_items:
        try:
            font = ImageFont.truetype(path, font_size)
            bbox = draw.textbbox((0,0), name, font=font)
            text_y = y + (line_height - (bbox[3] - bbox[1])) / 2
            draw.text((padding, text_y), name, font=font, fill=font_name_color)
            example_bbox = draw.textbbox((0, 0), example_text, font=font)
            example_x = img_width - padding - (example_bbox[2] - example_bbox[0])
            draw.text((example_x, text_y), example_text, font=font, fill=example_color)
            y += line_height
        except Exception as e:
            print(f"Не удалось загрузить шрифт {name}: {e}")

    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='JPEG', quality=95)
    img_byte_arr.seek(0)
    return img_byte_arr
