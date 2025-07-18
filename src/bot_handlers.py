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


# --- Вспомогательная функция для создания меню ---

async def display_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отображает главное меню с текущими настройками и кнопками."""
    config = context.user_data.get('config', {})

    # Формируем текст с текущими настройками
    status_text = [
        "Текущие настройки вашего баннера:",
        f"<b>{BTN_WIDTH}:</b> {config.get('width', 'не задана')} мм",
        f"<b>{BTN_HEIGHT}:</b> {config.get('height', 'не задана')} мм",
        f"<b>{BTN_BG_COLOR}:</b> {config.get('bg_color', 'не задан')}",
        f"<b>{BTN_TEXT_COLOR}:</b> {config.get('text_color', 'не задан')}",
        f"<b>{BTN_FONT}:</b> {config.get('font', 'не задан')}",
    ]
    
    if 'text_lines' in config:
        text_preview = ' | '.join(config['text_lines'])
        status_text.append(f"<b>{BTN_TEXT_LINES}:</b> <i>«{text_preview}»</i>")
    else:
        status_text.append(f"<b>{BTN_TEXT_LINES}:</b> не задан")

    # Формируем клавиатуру
    buttons = [
        [BTN_WIDTH, BTN_HEIGHT],
        [BTN_BG_COLOR, BTN_TEXT_COLOR],
        [BTN_FONT, BTN_TEXT_LINES],
        [BTN_GENERATE],
        [BTN_CANCEL]
    ]
    keyboard = ReplyKeyboardMarkup(buttons, resize_keyboard=True)

    await update.message.reply_text(
        "\n".join(status_text),
        reply_markup=keyboard,
        parse_mode='HTML'
    )


# --- Функции диалога ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начинает диалог и показывает главное меню."""
    context.user_data['config'] = {}
    await update.message.reply_text("Привет! Давайте создадим ваш баннер. Используйте кнопки ниже для настройки.")
    await display_menu(update, context)
    return MAIN_MENU

async def ask_for_width(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(f"Введите ширину в мм (от {MIN_DIMENSION} до {MAX_DIMENSION}):", reply_markup=ReplyKeyboardRemove())
    return AWAIT_WIDTH

async def save_width(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        width = int(update.message.text)
        if not (MIN_DIMENSION <= width <= MAX_DIMENSION): raise ValueError
        context.user_data['config']['width'] = width
        await update.message.reply_text(f"✅ Ширина установлена: {width} мм")
    except (ValueError, TypeError):
        await update.message.reply_text(f"❌ Неверный формат. Введите число от {MIN_DIMENSION} до {MAX_DIMENSION}.")
    
    await display_menu(update, context)
    return MAIN_MENU

async def ask_for_height(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(f"Введите высоту в мм (от {MIN_DIMENSION} до {MAX_DIMENSION}):", reply_markup=ReplyKeyboardRemove())
    return AWAIT_HEIGHT

async def save_height(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        height = int(update.message.text)
        if not (MIN_DIMENSION <= height <= MAX_DIMENSION): raise ValueError
        context.user_data['config']['height'] = height
        await update.message.reply_text(f"✅ Высота установлена: {height} мм")
    except (ValueError, TypeError):
        await update.message.reply_text(f"❌ Неверный формат. Введите число от {MIN_DIMENSION} до {MAX_DIMENSION}.")
    
    await display_menu(update, context)
    return MAIN_MENU

async def ask_for_color(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Запрашивает цвет, запоминая, для чего он (фон или текст)."""
    # Сохраняем, какой цвет мы сейчас устанавливаем
    context.user_data['color_target'] = update.message.text 
    
    keyboard = [[f"{details['emoji']} {name}" for name, details in COLORS.items()][i:i+2] for i in range(0, len(COLORS), 2)]
    
    await update.message.reply_text("Выберите цвет:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
    return AWAIT_BG_COLOR # Используем один и тот же обработчик для обоих цветов

async def save_color(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        color_name = update.message.text.split(' ', 1)[1]
        if color_name not in COLORS: raise ValueError
        
        target_button = context.user_data.get('color_target')
        if target_button == BTN_BG_COLOR:
            context.user_data['config']['bg_color'] = color_name
            await update.message.reply_text(f"✅ Цвет фона установлен: {color_name}")
        elif target_button == BTN_TEXT_COLOR:
            context.user_data['config']['text_color'] = color_name
            await update.message.reply_text(f"✅ Цвет текста установлен: {color_name}")
            
    except (ValueError, IndexError):
        await update.message.reply_text("❌ Пожалуйста, выберите цвет, нажав на кнопку.")
        
    await display_menu(update, context)
    return MAIN_MENU

async def ask_for_font(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Готовлю превью шрифтов...", reply_markup=ReplyKeyboardRemove())
    try:
        font_preview = create_font_preview_image()
        await update.message.reply_photo(photo=font_preview, caption="Вот так выглядят доступные шрифты.")
    except Exception as e:
        logger.error(f"Ошибка при создании превью шрифтов: {e}", exc_info=True)
    
    keyboard = [[name] for name in FONTS.keys()]
    await update.message.reply_text("Выберите шрифт из списка:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
    return AWAIT_FONT_CHOICE

async def save_font(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    font = update.message.text
    if font in FONTS:
        context.user_data['config']['font'] = font
        await update.message.reply_text(f"✅ Шрифт установлен: {font}")
    else:
        await update.message.reply_text("❌ Пожалуйста, выберите шрифт из списка.")
        
    await display_menu(update, context)
    return MAIN_MENU

async def ask_for_line_count(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['config']['text_lines'] = [] # Очищаем старый текст
    keyboard = [["1", "2"], ["3", "4"]]
    await update.message.reply_text("Сколько строк текста будет на баннере?", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
    return AWAIT_LINE_COUNT

async def save_line_count_and_ask_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        count = int(update.message.text)
        if not 1 <= count <= 4: raise ValueError
        context.user_data['config']['line_count'] = count
        await update.message.reply_text(f"Отлично. Теперь введи текст для строки 1:", reply_markup=ReplyKeyboardRemove())
        return AWAIT_TEXT_LINES
    except (ValueError, TypeError):
        await update.message.reply_text("❌ Нажмите на одну из кнопок (1-4).")
        await display_menu(update, context)
        return MAIN_MENU

async def save_text_and_continue(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    config = context.user_data['config']
    config['text_lines'].append(update.message.text)
    
    collected = len(config['text_lines'])
    total = config['line_count']
    
    if collected < total:
        await update.message.reply_text(f"Принято. Введи текст для строки {collected + 1}:")
        return AWAIT_TEXT_LINES
    else:
        await update.message.reply_text("✅ Весь текст сохранен!")
        await display_menu(update, context)
        return MAIN_MENU

async def generate_banner(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Проверяет данные и запускает генерацию превью."""
    config = context.user_data.get('config', {})
    required_keys = ['width', 'height', 'bg_color', 'text_color', 'font', 'text_lines']
    
    if not all(key in config and config.get(key) for key in required_keys):
        await update.message.reply_text("❌ Пожалуйста, заполните все параметры перед генерацией.", reply_markup=ReplyKeyboardRemove())
        await display_menu(update, context)
        return MAIN_MENU

    await update.message.reply_text("Отлично! Все данные собраны, создаю превью...", reply_markup=ReplyKeyboardRemove())
    try:
        preview_image = create_preview_jpeg(config)
        keyboard = [[InlineKeyboardButton("✅ Да, сгенерировать PDF", callback_data="generate_pdf"), InlineKeyboardButton("❌ Отмена", callback_data="cancel_generation")]]
        await update.message.reply_photo(photo=preview_image, caption="Вот как будет выглядеть ваш баннер. Все верно?", reply_markup=InlineKeyboardMarkup(keyboard))
        return PREVIEW_CONFIRM
    except Exception as e:
        logger.error(f"Ошибка при создании превью: {e}", exc_info=True)
        await update.message.reply_text("Произошла ошибка при создании превью. Попробуйте снова.")
        await display_menu(update, context)
        return MAIN_MENU

# --- Функции колбэков и отмены ---

async def generate_pdf_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_caption(caption="⏳ Создаю финальный PDF-файл...")

    try:
        pdf_file = create_final_pdf(context.user_data['config'])
        filename = f"banner_{update.effective_user.id}_{context.user_data['config']['width']}x{context.user_data['config']['height']}.pdf"
        
        await context.bot.send_document(
            chat_id=TELEGRAM_CHANNEL_ID,
            document=pdf_file,
            filename=filename,
            caption=f"Новый баннер готов! Заказ от @{update.effective_user.username or update.effective_user.id}"
        )
        await query.edit_message_caption(caption="✅ Готово! Ваш баннер отправлен в канал.")
    except Exception as e:
        logger.error(f"Ошибка при создании или отправке PDF: {e}", exc_info=True)
        await query.edit_message_caption(caption="❌ Произошла ошибка при создании PDF.")
        
    context.user_data.clear()
    return ConversationHandler.END

async def back_to_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Возвращает в главное меню после отмены генерации PDF."""
    query = update.callback_query
    await query.answer()
    await query.delete_message()
    await update.effective_message.reply_text("Генерация отменена. Вы вернулись в главное меню.")
    await display_menu(update.effective_message, context) # effective_message важен здесь
    return MAIN_MENU

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Полностью отменяет диалог."""
    await update.message.reply_text("Действие отменено. Чтобы начать заново, отправьте /start.", reply_markup=ReplyKeyboardRemove())
    context.user_data.clear()
    return ConversationHandler.END
