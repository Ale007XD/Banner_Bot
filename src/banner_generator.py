import io
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.colors import CMYKColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from .config import SAFE_ZONE_MM, COLORS, FONTS

# Регистрация шрифтов в reportlab для корректной работы
for name, path in FONTS.items():
    pdfmetrics.registerFont(TTFont(name, path))

def _calculate_adaptive_font_size(draw, text_lines, font_path, safe_zone_px):
    """
    Адаптивно подбирает максимальный размер шрифта, чтобы все строки текста
    вмещались в безопасную зону.
    """
    safe_width_px, safe_height_px = safe_zone_px
    font_size = 300  # Начинаем с большого размера
    
    while font_size > 10:
        font = ImageFont.truetype(font_path, font_size)
        
        # Рассчитываем общую высоту и максимальную ширину для всех строк
        total_text_height = 0
        max_text_width = 0
        line_spacing = font_size * 0.2  # Межстрочный интервал
        
        for i, line in enumerate(text_lines):
            bbox = draw.textbbox((0, 0), line, font=font)
            line_width = bbox - bbox
            line_height = bbox - bbox
            
            if line_width > max_text_width:
                max_text_width = line_width
            
            total_text_height += line_height
            if i < len(text_lines) - 1:
                total_text_height += line_spacing

        if max_text_width < safe_width_px and total_text_height < safe_height_px:
            return font, font_size  # Найден подходящий размер
            
        font_size -= 5 # Уменьшаем размер и пробуем снова
        
    return ImageFont.truetype(font_path, 10), 10 # Возвращаем минимальный размер, если не влезло

def create_preview_jpeg(data):
    """Создает JPEG превью баннера."""
    width_mm, height_mm = data['width'], data['height']
    bg_color_name, text_color_name = data['bg_color'], data['text_color']
    text_lines, font_name = data['text_lines'], data['font']

    # Для превью делаем масштаб, чтобы изображение не было гигантским
    scale = 1.0  # 1 пиксель = 1 мм
    width_px, height_px = int(width_mm * scale), int(height_mm * scale)

    bg_color_rgb = COLORS[bg_color_name]['rgb']
    text_color_rgb = COLORS[text_color_name]['rgb']
    font_path = FONTS[font_name]

    # Создаем изображение
    image = Image.new("RGB", (width_px, height_px), bg_color_rgb)
    draw = ImageDraw.Draw(image)

    # Определяем безопасную зону в пикселях
    safe_zone_px_x = SAFE_ZONE_MM * scale
    safe_zone_px_y = SAFE_ZONE_MM * scale
    safe_width = width_px - 2 * safe_zone_px_x
    safe_height = height_px - 2 * safe_zone_px_y

    # Подбираем шрифт
    font, font_size = _calculate_adaptive_font_size(draw, text_lines, font_path, (safe_width, safe_height))
    
    # Центрируем блок текста
    line_spacing = font_size * 0.2
    total_text_height = sum(draw.textbbox((0, 0), line, font=font) - draw.textbbox((0, 0), line, font=font) for line in text_lines) + line_spacing * (len(text_lines) - 1)
    
    y = (height_px - total_text_height) / 2

    for line in text_lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_width = bbox - bbox
        line_height = bbox - bbox
        x = (width_px - line_width) / 2
        draw.text((x, y), line, font=font, fill=text_color_rgb)
        y += line_height + line_spacing

    # Сохраняем в байтовый поток
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='JPEG', quality=90)
    img_byte_arr.seek(0)
    return img_byte_arr

def create_final_pdf(data):
    """Создает финальный PDF баннер с CMYK цветами и встроенными шрифтами."""
    width_mm, height_mm = data['width'], data['height']
    bg_color_name, text_color_name = data['bg_color'], data['text_color']
    text_lines, font_name = data['text_lines'], data['font']

    # Получаем CMYK значения
    c, m, y, k = COLORS[bg_color_name]['cmyk']
    bg_color_cmyk = CMYKColor(c/100, m/100, y/100, k/100)
    
    c, m, y, k = COLORS[text_color_name]['cmyk']
    text_color_cmyk = CMYKColor(c/100, m/100, y/100, k/100)
    
    pdf_buffer = io.BytesIO()
    
    # Создаем холст с физическими размерами
    c = canvas.Canvas(pdf_buffer, pagesize=(width_mm * mm, height_mm * mm))

    # Рисуем фон
    c.setFillColor(bg_color_cmyk)
    c.rect(0, 0, width_mm * mm, height_mm * mm, fill=1, stroke=0)
    
    # Устанавливаем цвет для текста
    c.setFillColor(text_color_cmyk)

    # --- Логика размещения и масштабирования текста для PDF ---
    safe_width = (width_mm - 2 * SAFE_ZONE_MM) * mm
    safe_height = (height_mm - 2 * SAFE_ZONE_MM) * mm
    
    # Подбираем размер шрифта (аналогично превью, но с использованием reportlab)
    font_size = 300
    line_spacing_ratio = 1.2
    
    while font_size > 10:
        c.setFont(font_name, font_size)
        face = pdfmetrics.getFont(font_name).face
        
        max_line_width = max(pdfmetrics.stringWidth(line, font_name, font_size) for line in text_lines)
        total_text_height = (face.ascent - face.descent) / 1000 * font_size * len(text_lines) * line_spacing_ratio
        
        if max_line_width < safe_width and total_text_height < safe_height:
            break
        font_size -= 5
    
    c.setFont(font_name, font_size)
    face = pdfmetrics.getFont(font_name).face
    line_height = (face.ascent - face.descent) / 1000 * font_size * line_spacing_ratio
    total_text_height = line_height * len(text_lines)
    
    # Центрируем блок текста
    y_start = (height_mm * mm + total_text_height) / 2 - (face.ascent / 1000 * font_size)

    for i, line in enumerate(text_lines):
        line_width = pdfmetrics.stringWidth(line, font_name, font_size)
        x_start = (width_mm * mm - line_width) / 2
        
        # Создаем текстовый объект
        text_object = c.beginText()
        text_object.setTextOrigin(x_start, y_start - i * line_height)
        text_object.setFont(font_name, font_size)
        text_object.textLine(line)

        # Рисуем текстовый объект, reportlab сам встроит шрифты
        c.drawText(text_object)

    c.showPage()
    c.save()
    
    pdf_buffer.seek(0)
    return pdf_buffer

def create_font_preview_image():
    """Создает JPEG-изображение с примерами всех доступных шрифтов."""
    font_items = list(FONTS.items())
    
    img_width = 800
    line_height = 80
    padding = 40
    img_height = len(font_items) * line_height + 2 * padding
    bg_color = (240, 240, 240)
    
    image = Image.new("RGB", (img_width, img_height), bg_color)
    draw = ImageDraw.Draw(image)
    
    y = padding
    for name, path in font_items:
        try:
            sample_text = name
            font_size = 40
            font = ImageFont.truetype(path, font_size)
            
            text_y = y + (line_height - font_size) / 2
            
            draw.text(
                (padding, text_y), 
                sample_text, 
                font=font, 
                fill=(0, 0, 0)
            )
            y += line_height
        except Exception as e:
            print(f"Не удалось загрузить шрифт {name}: {e}")

    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='JPEG', quality=95)
    img_byte_arr.seek(0)
    return img_byte_arr
