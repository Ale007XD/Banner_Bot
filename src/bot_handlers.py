import logging
import telegram
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from .config import *
from .order_manager import get_next_order_number
from .banner_generator import create_preview_jpeg, create_final_pdf, create_font_preview_image

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


# --- Вспомогательная функция для создания меню ---

async def display_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Отображает главное меню с текущими настройками и кнопками,
    подсвечивая заданные и незаданные параметры.
    """
    message = update.message if hasattr(update, 'message') else update
    config = context.user_data.get('config', {})

    status_text = ["<b>Текущие настройки вашего баннера:</b>"]

    # --- ИЗМЕНЕНИЕ ЗДЕСЬ: Логика с индикаторами ---
    
    # Ширина
    if config.get('width'):
        status_text.append(f"🟢 <b>{BTN_WIDTH}:</b> {config['width']} мм")
    else:
        status_text.append(f"🔴 <b>{BTN_WIDTH}:</b> не задана")

    # Высота
    if config.get('height'):
        status_text.append(f"🟢 <b>{BTN_HEIGHT}:</b> {config['height']} мм")
    else:
        status_text.append(f"🔴 <b>{BTN_HEIGHT}:</b> не задана")

    # Цвет фона
    if config.get('bg_color'):
        status_text.append(f"🟢 <b>{BTN_BG_COLOR}:</b> {config['bg_color']}")
    else:
        status_text.append(f"🔴 <b>{BTN_BG_COLOR}:</b> не задан")

    # Цвет текста
    if config.get('text_color'):
        status_text.append(f"🟢 <b>{BTN_TEXT_COLOR}:</b> {config['text_color']}")
    else:
        status_text.append(f"🔴 <b>{BTN_TEXT_COLOR}:</b> не задан")

    # Шрифт
    if config.get('font'):
        status_text.append(f"🟢 <b>{BTN_FONT}:</b> {config['font']}")
    else:
        status_text.append(f"🔴 <b>{BTN_FONT}:</b> не задан")

    # Текст
    if config.get('text_lines'): # Проверяет, что список не пустой
        text_preview = ' | '.join(config['text_lines'])
        status_text.append(f"🟢 <b>{BTN_TEXT_LINES}:</b> <i>«{text_preview}»</i>")
    else:
        status_text.append(f"🔴 <b>{BTN_TEXT_LINES}:</b> не задан")


    # Формируем клавиатуру (остается без изменений)
    buttons = [
        [BTN_WIDTH, BTN_HEIGHT],
        [BTN_BG_COLOR, BTN_TEXT_COLOR],
        [BTN_FONT, BTN_TEXT_LINES],
        [BTN_GENERATE],
        [BTN_CANCEL]
    ]
    keyboard = ReplyKeyboardMarkup(buttons, resize_keyboard=True)

    await message.reply_text(
        "\n".join(status_text),
        reply_markup=keyboard,
        parse_mode='HTML'
    )


# --- Функции диалога ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['config'] = {}
    await update.message.reply_text("Привет! Давайте создадим ваш баннер. Используйте кнопки ниже для настройки.")
    await display_menu(update.message, context)
    return MAIN_MENU

# ... (все остальные функции остаются БЕЗ ИЗМЕНЕНИЙ) ...

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
    
    await display_menu(update.message, context)
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
    
    await display_menu(update.message, context)
    return MAIN_MENU

async def ask_for_color(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['color_target'] = update.message.text 
    keyboard = [[f"{details['emoji']} {name}" for name, details in COLORS.items()][i:i+2] for i in range(0, len(COLORS), 2)]
    await update.message.reply_text("Выберите цвет:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
    return AWAIT_BG_COLOR

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
    await display_menu(update.message, context)
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
    await display_menu(update.message, context)
    return MAIN_MENU

async def ask_for_line_count(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['config']['text_lines'] = []
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
        await display_menu(update.message, context)
        return MAIN_MENU

async def save_text_and_continue(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    config = context.user_data['config']
    config['text_lines'].append(update.message.text)
    collected = len(config['text_lines'])
    total = config.get('line_count', 0)
    if collected < total:
        await update.message.reply_text(f"Принято. Введи текст для строки {collected + 1}:")
        return AWAIT_TEXT_LINES
    else:
        await update.message.reply_text("✅ Весь текст сохранен!")
        await display_menu(update.message, context)
        return MAIN_MENU

async def generate_banner(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    config = context.user_data.get('config', {})
    required_keys = ['width', 'height', 'bg_color', 'text_color', 'font', 'text_lines']
    all_set = all(key in config and config.get(key) for key in required_keys)
    if not all_set or not config.get('text_lines'):
        await update.message.reply_text("❌ Пожалуйста, заполните все параметры перед генерацией.", reply_markup=ReplyKeyboardRemove())
        await display_menu(update.message, context)
        return MAIN_MENU
    await update.message.reply_text("Отлично! Все данные собраны, создаю превью...", reply_markup=ReplyKeyboardRemove())
    try:
        preview_image = create_preview_jpeg(config)
        keyboard = [[InlineKeyboardButton("✅ Да, сгенерировать PDF", callback_data="generate_pdf"), InlineKeyboardButton("❌ Назад в меню", callback_data="cancel_generation")]]
        await update.message.reply_photo(photo=preview_image, caption="Вот как будет выглядеть ваш баннер. Все верно?", reply_markup=InlineKeyboardMarkup(keyboard))
        return PREVIEW_CONFIRM
    except Exception as e:
        logger.error(f"Ошибка при создании превью: {e}", exc_info=True)
        await update.message.reply_text("Произошла ошибка при создании превью. Попробуйте снова.")
        await display_menu(update.message, context)
        return MAIN_MENU

async def generate_pdf_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_caption(caption="⏳ Присваиваю номер заказа и создаю PDF-файл...")
    try:
        order_number = get_next_order_number()
        pdf_file = create_final_pdf(context.user_data['config'])
        filename = f"order_{order_number}.pdf"
        channel_caption = (
            f"Новый заказ №{order_number}\n"
            f"От пользователя: @{update.effective_user.username or update.effective_user.id}"
        )
        await context.bot.send_document(
            chat_id=TELEGRAM_CHANNEL_ID,
            document=pdf_file,
            filename=filename,
            caption=channel_caption
        )
        await query.edit_message_caption(
            caption=f"✅ Готово! Вашему заказу присвоен номер {order_number}. Баннер отправлен в канал."
        )
    except Exception as e:
        logger.error(f"Ошибка при создании или отправке PDF: {e}", exc_info=True)
        await query.edit_message_caption(caption="❌ Произошла ошибка при создании PDF.")
    context.user_data['config'] = {}
    await query.message.reply_text("\nВы можете создать следующий баннер:")
    await display_menu(query.message, context)
    return MAIN_MENU

async def back_to_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.delete_message()
    await update.effective_message.reply_text("Генерация отменена. Вы вернулись в главное меню.")
    await display_menu(update.effective_message, context)
    return MAIN_MENU

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    keyboard = [[BTN_RESTART]]
    await update.message.reply_text(
        "Действие отменено.",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    )
    context.user_data.clear()
    return ConversationHandler.END
