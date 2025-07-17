import logging
import telegram
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from .config import *
from .banner_generator import create_preview_jpeg, create_final_pdf, create_font_preview_image

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начинает диалог и запрашивает ширину баннера."""
    context.user_data.clear()
    await update.message.reply_text(
        "Привет! Я бот для создания печатных баннеров.\n\n"
        f"Введи ширину баннера в миллиметрах (от {MIN_DIMENSION} до {MAX_DIMENSION}).\n\n"
        "Для отмены в любой момент напиши /cancel."
    )
    return WIDTH

async def get_width(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получает и проверяет ширину, запрашивает высоту."""
    try:
        width = int(update.message.text)
        if not (MIN_DIMENSION <= width <= MAX_DIMENSION):
            raise ValueError
        context.user_data['width'] = width
        await update.message.reply_text(
            f"Отлично, ширина: {width} мм.\n"
            f"Теперь введи высоту в мм (от {MIN_DIMENSION} до {MAX_DIMENSION})."
        )
        return HEIGHT
    except (ValueError, TypeError):
        await update.message.reply_text(
            f"Неверный формат. Пожалуйста, введи целое число от {MIN_DIMENSION} до {MAX_DIMENSION}."
        )
        return WIDTH

async def get_height(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получает и проверяет высоту, запрашивает цвет фона."""
    try:
        height = int(update.message.text)
        if not (MIN_DIMENSION <= height <= MAX_DIMENSION):
            raise ValueError
        context.user_data['height'] = height
        
        reply_keyboard = [[f"{details['emoji']} {name}"] for name, details in COLORS.items()]

        await update.message.reply_text(
            f"Высота: {height} мм. Теперь выбери цвет фона.",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
        )
        return BG_COLOR
    except (ValueError, TypeError):
        await update.message.reply_text(
            f"Неверный формат. Пожалуйста, введи целое число от {MIN_DIMENSION} до {MAX_DIMENSION}."
        )
        return HEIGHT

async def get_bg_color(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получает цвет фона, запрашивает количество строк."""
    raw_color_text = update.message.text
    try:
        color = raw_color_text.split(' ', 1)[1]
    except IndexError:
        color = raw_color_text 

    if color not in COLORS:
        await update.message.reply_text("Пожалуйста, выбери цвет из предложенных вариантов.")
        return BG_COLOR
    
    context.user_data['bg_color'] = color
    reply_keyboard = [["1", "2", "3", "4"]]
    await update.message.reply_text(
        f"Цвет фона: {color}. Сколько строк текста будет на баннере?",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True),
    )
    return LINE_COUNT

async def get_line_count(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получает количество строк и запрашивает первую строку."""
    try:
        count = int(update.message.text)
        if not (1 <= count <= 4):
            raise ValueError
        context.user_data['line_count'] = count
        context.user_data['text_lines'] = []
        context.user_data['current_line'] = 1
        await update.message.reply_text(
            f"Будет {count} строк(и). Введи текст для строки 1:",
            reply_markup=ReplyKeyboardRemove(),
        )
        return TEXT_LINES
    except (ValueError, TypeError):
        await update.message.reply_text("Пожалуйста, выбери количество строк от 1 до 4.")
        return LINE_COUNT

async def get_text_lines(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получает текст для каждой строки по очереди."""
    text = update.message.text
    context.user_data['text_lines'].append(text)
    
    current_line = context.user_data['current_line']
    total_lines = context.user_data['line_count']

    if current_line < total_lines:
        context.user_data['current_line'] += 1
        await update.message.reply_text(f"Отлично. Теперь введи текст для строки {current_line}:")
        return TEXT_LINES
    else:
        reply_keyboard = [[f"{details['emoji']} {name}"] for name, details in COLORS.items()]
        await update.message.reply_text(
            "Весь текст получен. Теперь выбери цвет текста.",
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
        )
        return TEXT_COLOR

async def get_text_color(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получает цвет текста, показывает превью шрифтов и запрашивает выбор."""
    raw_color_text = update.message.text
    try:
        color = raw_color_text.split(' ', 1)[1]
    except IndexError:
        color = raw_color_text

    if color not in COLORS:
        await update.message.reply_text("Пожалуйста, выбери цвет из предложенных вариантов.")
        return TEXT_COLOR
    
    context.user_data['text_color'] = color
    
    await update.message.reply_text(
        "Отлично! Готовлю превью доступных шрифтов...", 
        reply_markup=ReplyKeyboardRemove()
    )
    try:
        font_preview = create_font_preview_image()
        await update.message.reply_photo(
            photo=font_preview,
            caption="Вот так выглядят доступные шрифты."
        )
    except Exception as e:
        logger.error(f"Ошибка при создании превью шрифтов: {e}", exc_info=True)
        await update.message.reply_text("Не удалось создать превью шрифтов, но вы все равно можете выбрать их по названию.")

    reply_keyboard = [[font] for font in FONTS.keys()]
    await update.message.reply_text(
        f"Теперь выбери шрифт:",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True),
    )
    return FONT_CHOICE

async def get_font(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получает шрифт и генерирует превью."""
    font = update.message.text
    if font not in FONTS:
        await update.message.reply_text("Пожалуйста, выбери шрифт из предложенных вариантов.")
        return FONT_CHOICE
    context.user_data['font'] = font
    await update.message.reply_text(
        "Все данные собраны! Создаю превью...", reply_markup=ReplyKeyboardRemove()
    )
    
    try:
        preview_image = create_preview_jpeg(context.user_data)
        keyboard = [
            [
                InlineKeyboardButton("✅ Да, сгенерировать PDF", callback_data="generate_pdf"),
                InlineKeyboardButton("❌ Отмена", callback_data="cancel"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_photo(
            photo=preview_image,
            caption="Вот как будет выглядеть твой баннер. Все верно?",
            reply_markup=reply_markup,
        )
        return PREVIEW_CONFIRM
    except Exception as e:
        logger.error(f"Ошибка при создании превью: {e}", exc_info=True)
        await update.message.reply_text(
            "Произошла ошибка при создании превью. Попробуйте снова. /start"
        )
        return ConversationHandler.END

async def generate_pdf_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Колбэк для кнопки 'Да'. Генерирует и отправляет PDF."""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_caption(caption="⏳ Создаю финальный PDF-файл. Это может занять немного времени...")

    try:
        pdf_file = create_final_pdf(context.user_data)
        filename = f"banner_{update.effective_user.id}_{context.user_data['width']}x{context.user_data['height']}.pdf"
        
        await context.bot.send_document(
            chat_id=TELEGRAM_CHANNEL_ID,
            document=pdf_file,
            filename=filename,
            caption=f"Новый баннер готов! Заказ от пользователя @{update.effective_user.username or update.effective_user.id}"
        )
        
        await query.edit_message_caption(
            caption="✅ Готово! Твой баннер сгенерирован и отправлен в наш канал."
        )
    except Exception as e:
        logger.error(f"Ошибка при создании или отправке PDF: {e}", exc_info=True)
        await query.edit_message_caption(
            caption=f"❌ Произошла ошибка при создании PDF. Пожалуйста, попробуйте снова. /start"
        )
        
    context.user_data.clear()
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отменяет текущий диалог."""
    query = update.callback_query
    if query:
        await query.answer()
        try:
            await query.edit_message_caption(caption="Действие отменено.")
        except telegram.error.BadRequest as e:
            if "message is not modified" not in str(e).lower():
                logger.warning(f"Не удалось отредактировать сообщение при отмене, удаляю: {e}")
                await query.delete_message()
    else:
        await update.message.reply_text(
            "Действие отменено. Чтобы начать заново, введите /start.",
            reply_markup=ReplyKeyboardRemove(),
        )
    context.user_data.clear()
    return ConversationHandler.END
