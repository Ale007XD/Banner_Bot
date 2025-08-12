from .banner_generator import create_preview_jpeg, create_final_pdf, create_final_tiff
from .config import *
from .order_manager import get_next_order_number, get_stats
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes
import os

# Start handler - entry point for the conversation
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await display_menu(update, context)
    return MAIN_MENU

# Display main menu with current settings
async def display_menu(update, context: ContextTypes.DEFAULT_TYPE):
    """Формирует и показывает главное меню с кнопками основных этапов."""
    config = context.user_data.get('config', {'postprint': POSTPRINT_NONE})
    
    # Формируем кнопки основных этапов на основе констант BTN_*
    buttons = [
        [BTN_ADD_TEXT],
        [BTN_CHANGE_COLOR],
        [BTN_SCALE_TEXT],
        [BTN_SELECT_POSTPRINT],
        [BTN_GENERATE_PREVIEW],
        [BTN_SHOW_STATS]
    ]
    
    # Показываем текущие настройки пользователя
    current_postprint = config.get('postprint', POSTPRINT_NONE)
    text_lines_count = len(config.get('text_lines', []))
    
    menu_text = f"🎨 **Создание баннера**\n\n📝 Строк текста: {text_lines_count}\n🔩 Постпечать: {current_postprint}\n\nВыберите действие:"
    
    if hasattr(update, 'message') and update.message:
        await update.message.reply_text(menu_text, reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True), parse_mode='Markdown')
    else:
        # Для случаев когда update - это объект сообщения
        await update.reply_text(menu_text, reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True), parse_mode='Markdown')

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
    except (ValueError, IndexError): 
        return AWAIT_LINE_FOR_SCALE

async def save_scale(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        line_index = context.user_data.pop('scale_line_index')
        scale_value = int(update.message.text.replace('%', '')) / 100.0
        context.user_data['config']['text_lines'][line_index]['scale'] = scale_value
    except (KeyError, IndexError, ValueError):
        await update.message.reply_text("❌ Ошибка.")
    await display_menu(update.message, context)
    return MAIN_MENU

# --- ДОБАВИТЬ НОВУЮ ФУНКЦИЮ ДЛЯ СТАТИСТИКИ ---
async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Показывает статистику заказов."""
    stats = get_stats()
    await update.message.reply_text(stats, parse_mode='Markdown')
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
    
    if not config.get('text_lines'):
        await update.message.reply_text("❌ Сначала добавьте текст!")
        await display_menu(update.message, context)
        return MAIN_MENU
    
    await update.message.reply_text("⏳ Создаю превью...")
    
    try:
        preview_data = create_preview_jpeg(config)
        
        # Создаем inline-клавиатуру с исправленными callback_data
        keyboard = [
            [
                InlineKeyboardButton("📄 Создать PDF", callback_data=CALLBACK_GENERATE_PDF),
                InlineKeyboardButton("🔙 В меню", callback_data=CALLBACK_BACK_TO_MENU)
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Исправленный вызов reply_photo (убрана лишняя закрывающая скобка)
        await update.message.reply_photo(
            photo=preview_data,
            caption="✅ Превью готово! Выберите действие:",
            reply_markup=reply_markup
        )
        
        return PREVIEW_STATE
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка создания превью: {str(e)}")
        await display_menu(update.message, context)
        return MAIN_MENU

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
    
    with open(file_path, 'wb') as f: 
        f.write(pdf_file_data.getbuffer())
    
    context.bot_data['last_order_path'] = file_path
    user_link = f"[{user.first_name}](tg://user?id={user.id})"
    channel_caption = f"✅ **Новый заказ №{order_number}**\n\n👤 **Заказчик:** {user_link}\n💬 **Username:** @{user.username or 'не указан'}\n\n🔩 **Постпечать:** {config['postprint']}"
    
    await context.bot.send_document(
        chat_id=TELEGRAM_CHANNEL_ID, 
        document=pdf_file_data, 
        filename=filename, 
        caption=channel_caption, 
        parse_mode='Markdown'
    )
    
    # Генерация и отправка TIFF
    await query.edit_message_caption(caption="⏳ Создаю TIFF-файл...")
    tiff_file_data = create_final_tiff(config)
    tiff_filename = f"order_{order_number}_{postprint_code}.tiff"
    tiff_file_path = os.path.join(orders_dir, tiff_filename)
    
    with open(tiff_file_path, 'wb') as f:
        f.write(tiff_file_data.getbuffer())
    
    await context.bot.send_document(
        chat_id=TELEGRAM_CHANNEL_ID,
        document=tiff_file_data,
        filename=tiff_filename,
        caption=f"📄 TIFF версия заказа №{order_number}",
        parse_mode='Markdown'
    )
    
    await query.edit_message_caption(caption=f"✅ Готово! Ваш заказ №{order_number} отправлен в канал.")
    context.user_data['config'] = {'postprint': POSTPRINT_NONE}
    
    await query.message.reply_text("\nВы можете создать следующий баннер:")
    await display_menu(query.message, context)
    return MAIN_MENU

async def back_to_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.delete_message()
    await display_menu(query.message, context)
    return MAIN_MENU
