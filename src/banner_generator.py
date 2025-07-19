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

def _calculate_font_size_proportional(draw, text_lines, font_path, safe_width, safe_height):
    if not text_lines or not any(text_lines):
        return ImageFont.truetype(font_path, 10), 10
    longest_line = max(text_lines, key=len)
    ref_size = 100
    ref_font = ImageFont.truetype(font_path, ref_size)
    ref_bbox = draw.textbbox((0, 0), longest_line, font=ref_font)
    ref_width = ref_bbox[2] - ref_bbox[0]
    if ref_width == 0: return ImageFont.truetype(font_path, 10), 10
    font_size_by_width = ref_size * (safe_width / ref_width)
    line_spacing_ratio = 1.2
    total_lines = len(text_lines)
    font_size_by_height = safe_height / (total_lines * line_spacing_ratio)
    final_font_size = min(font_size_by_width, font_size_by_height)
    final_font = ImageFont.truetype(font_path, int(final_font_size))
    return final_font, int(final_font_size)

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

    font, font_size = _calculate_font_size_proportional(draw, text_lines, font_path, safe_width, safe_height)
    
    line_spacing = font_size * 0.2
    line_heights = [draw.textbbox((0,0), line, font=font)[3] - draw.textbbox((0,0), line, font=font)[1] for line in text_lines]
    total_text_height = sum(line_heights) + line_spacing * (len(text_lines) - 1)
    
    y = (height_px - total_text_height) / 2

    for i, line in enumerate(text_lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        line_width = bbox[2] - bbox[0]
        
        # --- ИЗМЕНЕНИЕ ЗДЕСЬ (для превью) ---
        # Центрируем текст внутри безопасной зоны, а не по всей ширине баннера.
        x = safe_zone_px + (safe_width - line_width) / 2
        
        draw.text((x, y), line, font=font, fill=text_color_rgb)
        y += line_heights[i] + line_spacing

    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='JPEG', quality=90)
    img_byte_arr.seek(0)
    return img_byte_arr

def create_final_pdf(data):
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
    safe_height = (height_mm - 2 * SAFE_ZONE_MM) * mm

    ref_size = 100
    if not text_lines: text_lines = [" "] # Защита от пустого списка
    longest_line = max(text_lines, key=lambda line: pdfmetrics.stringWidth(line, font_name, ref_size))
    ref_width = pdfmetrics.stringWidth(longest_line, font_name, ref_size)
    
    font_size_by_width = ref_size * (safe_width / ref_width) if ref_width != 0 else 10
    
    line_spacing_ratio = 1.2
    total_lines = len(text_lines)
    font_size_by_height = safe_height / (total_lines * line_spacing_ratio)
    
    font_size = min(font_size_by_width, font_size_by_height)
    
    c.setFont(font_name, font_size)
    face = pdfmetrics.getFont(font_name).face
    line_height_pdf = (face.ascent - face.descent) / 1000 * font_size * line_spacing_ratio
    total_text_height_final = line_height_pdf * (len(text_lines) -1) + (face.ascent - face.descent) / 1000 * font_size
    
    y_start = (height_mm * mm + total_text_height_final) / 2 - (face.ascent / 1000 * font_size)

    for i, line in enumerate(text_lines):
        line_width_pdf = pdfmetrics.stringWidth(line, font_name, font_size)
        
        # --- ИЗМЕНЕНИЕ ЗДЕСЬ (для PDF) ---
        # Центрируем текст внутри безопасной зоны (30мм слева + (ширина зоны - ширина текста)/2)
        x_start = (SAFE_ZONE_MM * mm) + (safe_width - line_width_pdf) / 2
        
        text_object = c.beginText()
        text_object.setTextOrigin(x_start, y_start - i * line_height_pdf)
        text_object.setFont(font_name, font_size)
        text_object.textLine(line)
        c.drawText(text_object)

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
