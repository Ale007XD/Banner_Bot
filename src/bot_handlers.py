import logging
import os
import telegram
from functools import wraps
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from .config import *
from .order_manager import get_next_order_number, get_stats
from .banner_generator import create_preview_jpeg, create_final_pdf, create_font_preview_image

# --- (Админ-часть без изменений) ---
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)
def admin_only(func):
    @wraps(func)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if str(update.effective_user.id) != ADMIN_TELEGRAM_ID:
            await update.message.reply_text("⛔️ У вас нет прав для выполнения этой команды.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapped
@admin_only
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(get_stats(), parse_mode='MarkdownV2')
@admin_only
async def last_order_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    last_order_path = context.bot_data.get('last_order_path')
    if last_order_path and os.path.exists(last_order_path):
        await update.message.reply_document(document=open(last_order_path, 'rb'), caption=f"Последний заказ: `{os.path.basename(last_order_path)}`", parse_mode='MarkdownV2')
    else:
        await update.message.reply_text("Еще не было создано ни одного заказа с момента последнего перезапуска.")

# --- Основная логика ---

async def display_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message if hasattr(update, 'message') else update
    config = context.user_data.get('config', {})
    status_text = ["<b>Текущие настройки вашего баннера:</b>"]
    # ... (статус-блок)
    params = {
        BTN_WIDTH: config.get('width', 'не задана'),
        BTN_HEIGHT: config.get('height', 'не задана'),
        BTN_BG_COLOR: config.get('bg_color', 'не задан'),
        BTN_TEXT_COLOR: config.get('text_color', 'не задан'),
        BTN_FONT: config.get('font', 'не задан'),
    }
    for btn, val in params.items():
        icon = "🟢" if "не зада" not in str(val) else "🔴"
        status_text.append(f"{icon} <b>{btn}:</b> {val}")
    
    # --- ИЗМЕНЕНИЕ: Отображение текста с масштабом ---
    if config.get('text_lines'):
        text_parts = [f"«{item['text']}» ({int(item.get('scale', 1.0)*100)}%)" for item in config['text_lines']]
        text_preview = '\n- '.join(text_parts)
        status_text.append(f"🟢 <b>{BTN_TEXT_LINES}:</b>\n- {text_preview}")
    else:
        status_text.append(f"🔴 <b>{BTN_TEXT_LINES}:</b> не задан")
    
    # ... (статус постпечати)
    if config.get('postprint'): status_text.append(f"🟢 <b>{BTN_POSTPRINT}:</b> {config['postprint']}")
    else: status_text.append(f"🔴 <b>{BTN_POSTPRINT}:</b> не задана")

    # --- ИЗМЕНЕНИЕ: Динамическая клавиатура с новой кнопкой ---
    buttons = [[BTN_WIDTH, BTN_HEIGHT], [BTN_BG_COLOR, BTN_TEXT_COLOR], [BTN_FONT, BTN_POSTPRINT]]
    text_buttons = [BTN_TEXT_LINES]
    if config.get('text_lines'):
        text_buttons.extend([BTN_EDIT_TEXT, BTN_SCALE_TEXT])
    buttons.append(text_buttons)
    buttons.append([BTN_GENERATE])
    buttons.append([BTN_CANCEL])
    keyboard = ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    await message.reply_text("\n".join(status_text), reply_markup=keyboard, parse_mode='HTML')

# --- (start, ask/save width/height/color/font без изменений) ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['config'] = {'postprint': POSTPRINT_NONE}
    await update.message.reply_text("Привет! Давайте создадим ваш баннер. Используйте кнопки ниже для настройки.")
    await display_menu(update.message, context)
    return MAIN_MENU
async def ask_for_width(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(f"Введите ширину в мм (от {MIN_DIMENSION} до {MAX_DIMENSION}):", reply_markup=ReplyKeyboardRemove())
    return AWAIT_WIDTH
async def save_width(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        width = int(update.message.text)
        if not (MIN_DIMENSION <= width <= MAX_DIMENSION): raise ValueError
        context.user_data['config']['width'] = width
    except (ValueError, TypeError):
        await update.message.reply_text(f"❌ Неверный формат.")
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
    except (ValueError, TypeError):
        await update.message.reply_text(f"❌ Неверный формат.")
    await display_menu(update.message, context)
    return MAIN_MENU
async def ask_for_color(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['color_target'] = update.message.text
    keyboard = [[f"{details['emoji']} {name}" for name, details in COLORS.items()][i:i + 2] for i in range(0, len(COLORS), 2)]
    await update.message.reply_text("Выберите цвет:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
    return AWAIT_BG_COLOR
async def save_color(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        color_name = update.message.text.split(' ', 1)[1]
        if color_name not in COLORS: raise ValueError
        target_button = context.user_data.get('color_target')
        if target_button == BTN_BG_COLOR: context.user_data['config']['bg_color'] = color_name
        elif target_button == BTN_TEXT_COLOR: context.user_data['config']['text_color'] = color_name
    except (ValueError, IndexError):
        await update.message.reply_text("❌ Пожалуйста, выберите цвет, нажав на кнопку.")
    await display_menu(update.message, context)
    return MAIN_MENU
async def ask_for_font(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Готовлю превью шрифтов...", reply_markup=ReplyKeyboardRemove())
    font_preview = create_font_preview_image()
    await update.message.reply_photo(photo=font_preview, caption="Вот так выглядят доступные шрифты.")
    font_names = list(FONTS.keys())
    keyboard = [font_names[i:i + 2] for i in range(0, len(font_names), 2)]
    await update.message.reply_text("Выберите шрифт из списка:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
    return AWAIT_FONT_CHOICE
async def save_font(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text in FONTS: context.user_data['config']['font'] = update.message.text
    await display_menu(update.message, context)
    return MAIN_MENU
async def ask_for_line_count(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['config']['text_lines'] = []
    await update.message.reply_text("Сколько строк текста будет на баннере?", reply_markup=ReplyKeyboardMarkup([["1", "2"], ["3", "4"]], resize_keyboard=True))
    return AWAIT_LINE_COUNT

async def save_line_count_and_ask_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        count = int(update.message.text)
        if not 1 <= count <= 4: raise ValueError
        context.user_data['config']['line_count'] = count
        await update.message.reply_text(f"Отлично. Теперь введи текст для строки 1:", reply_markup=ReplyKeyboardRemove())
        return AWAIT_TEXT_LINES
    except (ValueError, TypeError):
        await display_menu(update.message, context)
        return MAIN_MENU

# --- ИЗМЕНЕНИЕ: Сохраняем текст в новом формате ---
async def save_text_and_continue(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    config = context.user_data['config']
    config.setdefault('text_lines', []).append({'text': update.message.text, 'scale': 1.0})
    if len(config['text_lines']) < config.get('line_count', 0):
        await update.message.reply_text(f"Принято. Введи текст для строки {len(config['text_lines']) + 1}:")
        return AWAIT_TEXT_LINES
    else:
        await update.message.reply_text("✅ Весь текст сохранен!")
        await display_menu(update.message, context)
        return MAIN_MENU

# --- ИЗМЕНЕНИЕ: Работаем с новой структурой данных ---
async def ask_which_line_to_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text_items = context.user_data.get('config', {}).get('text_lines', [])
    buttons = [[f"Строка {i + 1}: «{item['text'][:20]}...»"] for i, item in enumerate(text_items)] + [[BTN_BACK]]
    await update.message.reply_text("Какую строку вы хотите изменить?", reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True))
    return AWAIT_LINE_CHOICE_FOR_EDIT
async def ask_for_new_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        line_index = int(update.message.text.split(':')[0].split(' ')[1]) - 1
        context.user_data['edit_line_index'] = line_index
        await update.message.reply_text(f"Введите новый текст для строки {line_index + 1}:", reply_markup=ReplyKeyboardRemove())
        return AWAIT_NEW_TEXT
    except (ValueError, IndexError): return AWAIT_LINE_CHOICE_FOR_EDIT
async def save_edited_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    line_index = context.user_data.pop('edit_line_index')
    context.user_data['config']['text_lines'][line_index]['text'] = update.message.text
    await display_menu(update.message, context)
    return MAIN_MENU

# --- НОВЫЕ ФУНКЦИИ для масштабирования ---
async def ask_which_line_to_scale(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text_items = context.user_data.get('config', {}).get('text_lines', [])
    buttons = [[f"Строка {i+1} ({int(item.get('scale', 1.0)*100)}%)"] for i, item in enumerate(text_items)] + [[BTN_BACK]]
    await update.message.reply_text("Какую строку масштабировать?", reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True))
    return AWAIT_LINE_FOR_SCALE
async def ask_for_percentage(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        line_index = int(update.message.text.split(' ')[1]) - 1
        context.user_data['scale_line_index'] = line_index
        buttons = [["100%", "90%"], ["80%", "70%"], ["60%", "50%"], [BTN_BACK]]
        await update.message.reply_text(f"Выберите новый масштаб для строки {line_index + 1}:", reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True))
        return AWAIT_PERCENTAGE
    except (ValueError, IndexError): return AWAIT_LINE_FOR_SCALE
async def save_scale(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        line_index = context.user_data.pop('scale_line_index')
        scale_value = int(update.message.text.replace('%', '')) / 100.0
        context.user_data['config']['text_lines'][line_index]['scale'] = scale_value
    except (KeyError, IndexError, ValueError):
        await update.message.reply_text("❌ Ошибка.")
    await display_menu(update.message, context)
    return MAIN_MENU

# ... (остальные функции без изменений)
async def back_to_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await display_menu(update.message, context)
    return MAIN_MENU
async def ask_for_postprint(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Выберите вариант постпечатной обработки:", reply_markup=ReplyKeyboardMarkup([[key] for key in POSTPRINT_OPTIONS.keys()], resize_keyboard=True))
    return AWAIT_POSTPRINT
async def save_postprint(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text in POSTPRINT_OPTIONS:
        context.user_data['config']['postprint'] = update.message.text
    await display_menu(update.message, context)
    return MAIN_MENU
async def generate_preview(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    config = context.user_data.get('config', {})
    if not all(k in config for k in ['width', 'height', 'bg_color', 'text_color', 'font', 'text_lines', 'postprint']):
        await update.message.reply_text("❌ Пожалуйста, заполните все параметры.", reply_markup=ReplyKeyboardRemove())
        await display_menu(update.message, context)
        return MAIN_MENU
    await update.message.reply_text("Создаю превью...", reply_markup=ReplyKeyboardRemove())
    preview_image = create_preview_jpeg(config)
    await update.message.reply_photo(photo=preview_image, caption="Все верно?", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ Да, сгенерировать PDF", callback_data="generate_pdf"), InlineKeyboardButton("❌ Назад в меню", callback_data="cancel_generation")]]))
    return PREVIEW_CONFIRM
async def generate_pdf_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_caption(caption="⏳ Создаю PDF-файл...")
    config = context.user_data['config']
    user = update.effective_user
    order_number = get_next_order_number()
    pdf_file_data = create_final_pdf(config)
    postprint_code = POSTPRINT_OPTIONS.get(config['postprint'], "XX")
    filename = f"order_{order_number}_{postprint_code}.pdf"
    orders_dir = "orders"
    os.makedirs(orders_dir, exist_ok=True)
    file_path = os.path.join(orders_dir, filename)
    with open(file_path, 'wb') as f: f.write(pdf_file_data.getbuffer())
    context.bot_data['last_order_path'] = file_path
    user_link = f"[{user.first_name}](tg://user?id={user.id})"
    channel_caption = f"✅ **Новый заказ №{order_number}**\n\n👤 **Заказчик:** {user_link}\n💬 **Username:** @{user.username or 'не указан'}\n\n🔩 **Постпечать:** {config['postprint']}"
    await context.bot.send_document(chat_id=TELEGRAM_CHANNEL_ID, document=pdf_file_data, filename=filename, caption=channel_caption, parse_mode='Markdown')
    await query.edit_message_caption(caption=f"✅ Готово! Ваш заказ №{order_number} отправлен в канал.")
    context.user_data['config'] = {'postprint': POSTPRINT_NONE}
    await query.message.reply_text("\nВы можете создать следующий баннер:")
    await display_menu(query.message, context)
    return MAIN_MENU
async def back_to_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.delete_message()
    await display_menu(update.effective_message, context)
    return MAIN_MENU
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Действие отменено.", reply_markup=ReplyKeyboardMarkup([[BTN_RESTART]], resize_keyboard=True, one_time_keyboard=True))
    context.user_data.clear()
    return ConversationHandler.END
