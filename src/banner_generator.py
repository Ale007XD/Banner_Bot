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
    width_mm, height_mm = data['width'], data['height']
    bg_color_name, text_color_name = data['bg_color'], data['text_color']
    # --- ИЗМЕНЕНИЕ: Получаем список словарей, а не строк ---
    text_items, font_name = data['text_lines'], data['font']
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
    base_details = []
    
    # --- ИЗМЕНЕНИЕ: Учитываем индивидуальный масштаб для каждой строки ---
    for item in text_items:
        line = item['text']
        scale_modifier = item.get('scale', 1.0) # Получаем масштаб или 1.0
        if not line.strip(): continue
        
        effective_safe_width = safe_width * scale_modifier # Применяем масштаб
        ref_size = 100
        ref_font = ImageFont.truetype(font_path, ref_size)
        ref_bbox = draw.textbbox((0, 0), line, font=ref_font)
        ref_width = ref_bbox[2] - ref_bbox[0]
        if ref_width == 0: continue
        
        font_size = ref_size * (effective_safe_width / ref_width)
        font = ImageFont.truetype(font_path, int(font_size))
        line_bbox = draw.textbbox((0, 0), line, font=font)
        line_height = line_bbox[3] - line_bbox[1]
        base_details.append({'text': line, 'font_size': font_size, 'height': line_height})
    actual_total_height = sum(d['height'] * line_spacing_ratio for d in base_details)
    
    final_scale_factor = 1.0
    if actual_total_height > safe_height:
        final_scale_factor = safe_height / actual_total_height
    final_total_height = actual_total_height * final_scale_factor
    y = (height_px - final_total_height) / 2
    
    for detail in base_details:
        final_font_size = int(detail['font_size'] * final_scale_factor)
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
    width_mm, height_mm = data['width'], data['height']
    bg_color_name, text_color_name = data['bg_color'], data['text_color']
    # --- ИЗМЕНЕНИЕ: Получаем список словарей, а не строк ---
    text_items, font_name = data['text_lines'], data['font']
    pdf_buffer = io.BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=(width_mm * mm, height_mm * mm))
    if bg_color_name == 'Белый':
        c.setStrokeColorCMYK(0,0,0,0.3); c.setLineWidth(0.1); c.rect(0, 0, width_mm * mm, height_mm * mm, fill=0, stroke=1)
    else:
        c_bg, m_bg, y_bg, k_bg = COLORS[bg_color_name]['cmyk']
        c.setFillColorCMYK(c_bg/100, m_bg/100, y_bg/100, k_bg/100); c.rect(0, 0, width_mm * mm, height_mm * mm, fill=1, stroke=0)
    c_text, m_text, y_text, k_text = COLORS[text_color_name]['cmyk']
    c.setFillColorCMYK(c_text/100, m_text/100, y_text/100, k_text/100)
    safe_width = (width_mm - 2 * SAFE_ZONE_MM) * mm
    safe_height = (height_mm - 2 * SAFE_ZONE_MM) * mm
    line_spacing_ratio = 1.2
    base_details_pdf = []
    
    # --- ИЗМЕНЕНИЕ: Учитываем индивидуальный масштаб для каждой строки ---
    for item in text_items:
        line = item['text']
        scale_modifier = item.get('scale', 1.0)
        if not line.strip(): continue
        effective_safe_width = safe_width * scale_modifier
        ref_size = 100
        ref_width = pdfmetrics.stringWidth(line, font_name, ref_size)
        if ref_width == 0: continue
        font_size = ref_size * (effective_safe_width / ref_width)
        face = pdfmetrics.getFont(font_name).face
        line_height = (face.ascent - face.descent) / 1000 * font_size
        base_details_pdf.append({'text': line, 'font_size': font_size, 'height': line_height})
    actual_total_height_pdf = sum(d['height'] * line_spacing_ratio for d in base_details_pdf)
    final_scale_factor_pdf = 1.0
    if actual_total_height_pdf > safe_height: final_scale_factor_pdf = safe_height / actual_total_height_pdf
    final_total_height_pdf = actual_total_height_pdf * final_scale_factor_pdf
    y_start = (height_mm * mm + final_total_height_pdf) / 2
    for detail in base_details_pdf:
        final_font_size = detail['font_size'] * final_scale_factor_pdf
        final_line_height = detail['height'] * final_scale_factor_pdf
        c.setFont(font_name, final_font_size)
        face = pdfmetrics.getFont(font_name).face
        y_pos = y_start - (face.ascent / 1000 * final_font_size)
        final_width = pdfmetrics.stringWidth(detail['text'], font_name, final_font_size)
        x_start = (SAFE_ZONE_MM * mm) + (safe_width - final_width) / 2
        text_object = c.beginText(x_start, y_pos)
        text_object.setFont(font_name, final_font_size)
        text_object.textLine(detail['text'])
        c.drawText(text_object)
        y_start -= final_line_height * line_spacing_ratio
    c.showPage(); c.save(); pdf_buffer.seek(0)
    return pdf_buffer

def create_final_tiff(data):
    """Создает финальный TIFF файл высокого разрешения для печати"""
    width_mm, height_mm = data['width'], data['height']
    bg_color_name, text_color_name = data['bg_color'], data['text_color']
    text_items, font_name = data['text_lines'], data['font']
    
    # Высокое разрешение для печати (300 DPI)
    dpi = 300
    scale = dpi / 25.4  # мм в пиксели при 300 DPI
    width_px, height_px = int(width_mm * scale), int(height_mm * scale)
    
    bg_color_rgb = COLORS[bg_color_name]['rgb']
    text_color_rgb = COLORS[text_color_name]['rgb']
    font_path = FONTS[font_name]
    
    # Создаем изображение высокого разрешения
    image = Image.new("RGB", (width_px, height_px), bg_color_rgb)
    draw = ImageDraw.Draw(image)
    
    safe_zone_px = SAFE_ZONE_MM * scale
    safe_width = width_px - 2 * safe_zone_px
    safe_height = height_px - 2 * safe_zone_px
    
    line_spacing_ratio = 1.2
    base_details = []
    
    # Рассчитываем размеры для каждой строки
    for item in text_items:
        line = item['text']
        scale_modifier = item.get('scale', 1.0)
        if not line.strip(): continue
        
        effective_safe_width = safe_width * scale_modifier
        ref_size = 100
        ref_font = ImageFont.truetype(font_path, ref_size)
        ref_bbox = draw.textbbox((0, 0), line, font=ref_font)
        ref_width = ref_bbox[2] - ref_bbox[0]
        if ref_width == 0: continue
        
        font_size = ref_size * (effective_safe_width / ref_width)
        font = ImageFont.truetype(font_path, int(font_size))
        line_bbox = draw.textbbox((0, 0), line, font=font)
        line_height = line_bbox[3] - line_bbox[1]
        base_details.append({'text': line, 'font_size': font_size, 'height': line_height})
    
    actual_total_height = sum(d['height'] * line_spacing_ratio for d in base_details)
    
    # Масштабируем если не помещается
    final_scale_factor = 1.0
    if actual_total_height > safe_height:
        final_scale_factor = safe_height / actual_total_height
    final_total_height = actual_total_height * final_scale_factor
    y = (height_px - final_total_height) / 2
    
    # Рисуем текст
    for detail in base_details:
        final_font_size = int(detail['font_size'] * final_scale_factor)
        final_font = ImageFont.truetype(font_path, final_font_size)
        final_bbox = draw.textbbox((0, 0), detail['text'], font=final_font)
        final_width = final_bbox[2] - final_bbox[0]
        final_height = final_bbox[3] - final_bbox[1]
        x = safe_zone_px + (safe_width - final_width) / 2
        draw.text((x, y), detail['text'], font=final_font, fill=text_color_rgb)
        y += final_height * line_spacing_ratio
    
    # Сохраняем в TIFF с компрессией LZW
    tiff_buffer = io.BytesIO()
    image.save(tiff_buffer, format='TIFF', compression='lzw', dpi=(dpi, dpi))
    tiff_buffer.seek(0)
    return tiff_buffer

def create_font_preview_image():
    font_items = list(FONTS.items()); img_width, line_height, padding = 1200, 100, 50
    img_height = len(font_items) * line_height + 2 * padding
    bg_color, font_name_color, example_color = (240, 240, 240), (0, 0, 0), (80, 80, 80)
    image = Image.new("RGB", (img_width, img_height), bg_color)
    draw = ImageDraw.Draw(image)
    y = padding; example_text = "Продажа 123-45-67"; font_size = 40
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
        except Exception as e: print(f"Не удалось загрузить шрифт {name}: {e}")
    img_byte_arr = io.BytesIO(); image.save(img_byte_arr, format='JPEG', quality=95); img_byte_arr.seek(0)
    return img_byte_arr
