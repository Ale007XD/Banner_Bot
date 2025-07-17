import logging
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    CallbackQueryHandler,
)
from .config import TELEGRAM_BOT_TOKEN
from .bot_handlers import (
    start, get_width, get_height, get_bg_color, get_line_count, get_text_lines,
    get_text_color, get_font, generate_pdf_callback, cancel,
    WIDTH, HEIGHT, BG_COLOR, LINE_COUNT, TEXT_LINES, TEXT_COLOR, FONT_CHOICE, PREVIEW_CONFIRM
)

# Включаем логирование
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

def main() -> None:
    """Запуск бота."""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            WIDTH: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_width)],
            HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_height)],
            BG_COLOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_bg_color)],
            LINE_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_line_count)],
            TEXT_LINES: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_text_lines)],
            TEXT_COLOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_text_color)],
            FONT_CHOICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_font)],
            PREVIEW_CONFIRM: [
                CallbackQueryHandler(generate_pdf_callback, pattern="^generate_pdf$"),
                CallbackQueryHandler(cancel, pattern="^cancel$"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)
    
    # Добавляем глобальный обработчик /cancel
    application.add_handler(CommandHandler("cancel", cancel))
    
    logger.info("Бот запущен...")
    application.run_polling()

if __name__ == "__main__":
    main()
