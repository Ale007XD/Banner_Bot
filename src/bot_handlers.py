import logging
import os
import telegram
from functools import wraps
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from .config import *
from .order_manager import get_next_order_number, get_stats
from .banner_generator import create_preview_jpeg, create_final_pdf, create_font_preview_image

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


# --- ДЕКОРАТОР ДЛЯ ЗАЩИТЫ АДМИН-КОМАНД ---
def admin_only(func):
    @wraps(func)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if str(user_id) != ADMIN_TELEGRAM_ID:
            await update.message.reply_text("⛔️ У вас нет прав для выполнения этой команды.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapped


# --- АДМИН-КОМАНДЫ ---
@admin_only
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stats_text = get_stats()
    await update.message.reply_text(stats_text, parse_mode='MarkdownV2')

@admin_only
async def last_order_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    last_order_path = context.bot_data.get('last_order_path')
    if last_order_path and os.path.exists(last_order_path):
        await update.message.reply_document(
            document=open(last_order_path, 'rb'),
            caption=f"Последний заказ: `{os.path.basename(last_order_path)}`",
            parse_mode='MarkdownV2'
        )
    else:
        await update.message.reply_text("Еще не было создано ни одного заказа с момента последнего перезапуска.")


# --- Основная логика бота ---

async def display_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message if hasattr(update, 'message') else update
    config = context.user_data.get('config', {})
    status_text = ["<b>Текущие настройки вашего баннера:</b>"]
    if config.get('width'): status_text.append(f"🟢 <b>{BTN_WIDTH}:</b> {config['width']} мм")
    else: status_text.append(f"🔴 <b>{BTN_WIDTH}:</b> не задана")
    if config.get('height'): status_text.append(f"🟢 <b>{BTN_HEIGHT}:</b> {config['height']} мм")
    else: status_text.append(f"🔴 <b>{BTN_HEIGHT}:</b> не задана")
    if config.get('bg_color'): status_text.append(f"🟢 <b>{BTN_BG_COLOR}:</b> {config['bg_color']}")
    else: status_text.append(f"🔴 <b>{BTN_BG_COLOR}:</b> не задан")
    if config.get('text_color'): status_text.append(f"🟢 <b>{BTN_TEXT_COLOR}:</b> {config['text_color']}")
    else: status_text.append(f"🔴 <b>{BTN_TEXT_COLOR}:</b> не задан")
    if config.get('font'): status_text.append(f"🟢 <b>{BTN_FONT}:</b> {config['font']}")
    else: status_text.append(f"🔴 <b>{BTN_FONT}:</b> не задан")
    if config.get('text_lines'):
        text_preview = ' | '.join(config['text_lines'])
        status_text.append(f"🟢 <b>{BTN_TEXT_LINES}:</b> <i>«{text_preview}»</i>")
    else: status_text.append(f"🔴 <b>{BTN_TEXT_LINES}:</b> не задан")
    if config.get('postprint'): status_text.append(f"🟢 <b>{BTN_POSTPRINT}:</b> {config['postprint']}")
    else: status_text.append(f"🔴 <b>{BTN_POSTPRINT}:</b> не задана")
    buttons = [[BTN_WIDTH, BTN_HEIGHT], [BTN_BG_COLOR, BTN_TEXT_COLOR], [BTN_FONT, BTN_POSTPRINT]]
    text_buttons = [BTN_TEXT_LINES]
    if config.get('text_lines'): text_buttons.append(BTN_EDIT_TEXT)
    buttons.append(text_buttons)
    buttons.append([BTN_GENERATE])
    buttons.append([BTN_CANCEL])
    keyboard = ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    await message.reply_text("\n".join(status_text), reply_markup=keyboard, parse_mode='HTML')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['config'] = {'postprint': POSTPRINT_NONE}
    await update.message.reply_text("Привет! Давайте создадим ваш баннер. Используйте кнопки ниже для настройки.")
    await display_menu(update.message, context)
    return MAIN_MENU

# ... (все функции до ask_for_font остаются без изменений) ...
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

# --- Функция с изменением ---
async def ask_for_font(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Готовлю превью шрифтов...", reply_markup=ReplyKeyboardRemove())
    try:
        font_preview = create_font_preview_image()
        await update.message.reply_photo(photo=font_preview, caption="Вот так выглядят доступные шрифты.")
    except Exception as e:
        logger.error(f"Ошибка при создании превью шрифтов: {e}", exc_info=True)
    
    # --- ИЗМЕНЕНИЕ ЗДЕСЬ: Группируем кнопки по 2 в ряд ---
    font_names = list(FONTS.keys())
    keyboard = [font_names[i:i+2] for i in range(0, len(font_names), 2)]
    
    await update.message.reply_text("Выберите шрифт из списка:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
    return AWAIT_FONT_CHOICE

# ... (все остальные функции остаются без изменений) ...
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
async def ask_which_line_to_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text_lines = context.user_data.get('config', {}).get('text_lines', [])
    if not text_lines:
        await update.message.reply_text("Сначала введите текст.")
        await display_menu(update.message, context)
        return MAIN_MENU
    buttons = [[f"Строка {i+1}: «{line[:20]}...»"] for i, line in enumerate(text_lines)]
    buttons.append([BTN_BACK])
    keyboard = ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    await update.message.reply_text("Какую строку вы хотите изменить?", reply_markup=keyboard)
    return AWAIT_LINE_CHOICE_FOR_EDIT
async def ask_for_new_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        line_number_str = update.message.text.split(':')[0].split(' ')[1]
        line_index = int(line_number_str) - 1
        context.user_data['edit_line_index'] = line_index
        await update.message.reply_text(f"Введите новый текст для строки {line_number_str}:", reply_markup=ReplyKeyboardRemove())
        return AWAIT_NEW_TEXT
    except (ValueError, IndexError):
        await update.message.reply_text("❌ Пожалуйста, выберите строку из предложенных кнопок.")
        return AWAIT_LINE_CHOICE_FOR_EDIT
async def save_edited_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        line_index = context.user_data.pop('edit_line_index')
        context.user_data['config']['text_lines'][line_index] = update.message.text
        await update.message.reply_text("✅ Строка успешно изменена!")
    except (KeyError, IndexError):
        await update.message.reply_text("❌ Произошла ошибка. Попробуйте снова.")
    await display_menu(update.message, context)
    return MAIN_MENU
async def back_to_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await display_menu(update.message, context)
    return MAIN_MENU
async def ask_for_postprint(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    buttons = [[key] for key in POSTPRINT_OPTIONS.keys()]
    keyboard = ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    await update.message.reply_text("Выберите вариант постпечатной обработки (люверсы):", reply_markup=keyboard)
    return AWAIT_POSTPRINT
async def save_postprint(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    choice = update.message.text
    if choice in POSTPRINT_OPTIONS:
        context.user_data['config']['postprint'] = choice
        await update.message.reply_text(f"✅ Выбрано: {choice}")
    else:
        await update.message.reply_text("❌ Пожалуйста, выберите вариант из предложенных кнопок.")
    await display_menu(update.message, context)
    return MAIN_MENU
async def generate_banner(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    config = context.user_data.get('config', {})
    required_keys = ['width', 'height', 'bg_color', 'text_color', 'font', 'text_lines', 'postprint']
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
        config = context.user_data['config']
        order_number = get_next_order_number()
        pdf_file_data = create_final_pdf(config)
        postprint_code = POSTPRINT_OPTIONS.get(config['postprint'], "XX")
        filename = f"order_{order_number}_{postprint_code}.pdf"
        orders_dir = "orders"
        os.makedirs(orders_dir, exist_ok=True)
        file_path = os.path.join(orders_dir, filename)
        with open(file_path, 'wb') as f:
            f.write(pdf_file_data.getbuffer())
        context.bot_data['last_order_path'] = file_path
        channel_caption = (
            f"✅ Новый заказ №{order_number}\n\n"
            f"👤 От пользователя: @{update.effective_user.username or update.effective_user.id}\n"
            f"🔩 Постпечать: <b>{config['postprint']}</b>"
        )
        await context.bot.send_document(
            chat_id=TELEGRAM_CHANNEL_ID,
            document=pdf_file_data,
            filename=filename,
            caption=channel_caption,
            parse_mode='HTML'
        )
        await query.edit_message_caption(caption=f"✅ Готово! Вашему заказу присвоен номер {order_number}. Баннер отправлен в канал.")
    except Exception as e:
        logger.error(f"Ошибка при создании или отправке PDF: {e}", exc_info=True)
        await query.edit_message_caption(caption="❌ Произошла ошибка при создании PDF.")
    context.user_data['config'] = {'postprint': POSTPRINT_NONE}
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
    await update.message.reply_text("Действие отменено.", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True))
    context.user_data.clear()
    return ConversationHandler.END
