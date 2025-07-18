import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    CallbackQueryHandler,
)
from telegram.ext.filters import Regex
from .config import *
from .bot_handlers import *

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

def main() -> None:
    """Запуск бота с новой структурой диалога."""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Настройка кнопки "Меню" с командой /start
    application.bot.set_my_commands([
        ('start', '🚀 Создать новый баннер')
    ])

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MAIN_MENU: [
                MessageHandler(Regex(f'^{BTN_WIDTH}$'), ask_for_width),
                MessageHandler(Regex(f'^{BTN_HEIGHT}$'), ask_for_height),
                MessageHandler(Regex(f'^{BTN_BG_COLOR}$'), ask_for_color),
                MessageHandler(Regex(f'^{BTN_TEXT_COLOR}$'), ask_for_color),
                MessageHandler(Regex(f'^{BTN_FONT}$'), ask_for_font),
                MessageHandler(Regex(f'^{BTN_TEXT_LINES}$'), ask_for_line_count),
                MessageHandler(Regex(f'^{BTN_GENERATE}$'), generate_banner),
            ],
            AWAIT_WIDTH: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_width)],
            AWAIT_HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_height)],
            AWAIT_BG_COLOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_color)],
            AWAIT_FONT_CHOICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_font)],
            AWAIT_LINE_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_line_count_and_ask_text)],
            AWAIT_TEXT_LINES: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_text_and_continue)],
            PREVIEW_CONFIRM: [
                CallbackQueryHandler(generate_pdf_callback, pattern="^generate_pdf$"),
                CallbackQueryHandler(back_to_menu_callback, pattern="^cancel_generation$"),
            ],
        },
        fallbacks=[
            CommandHandler("start", start), # Можно перезапустить в любой момент
            MessageHandler(Regex(f'^{BTN_CANCEL}$'), cancel),
            CommandHandler("cancel", cancel),
        ],
        per_message=False,
    )

    application.add_handler(conv_handler)
    
    logger.info("Бот запущен с интерфейсом меню...")
    application.run_polling()

if __name__ == "__main__":
    main()
