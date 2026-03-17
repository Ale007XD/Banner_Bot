"""
main.py
Точка входа. PicklePersistence для сохранения FSM между перезапусками.
Webhook сбрасывается при старте — исключает конфликт с другими процессами.
"""

import logging

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    PicklePersistence,
    filters,
    PreCheckoutQueryHandler,
)
from telegram.ext.filters import Regex

from .payment_handlers import (
    pre_checkout_handler,
    successful_payment_handler,
)

from .bot_handlers import (
    ask_for_color,
    ask_for_font,
    ask_for_height,
    ask_for_line_count,
    ask_for_new_text,
    ask_for_percentage,
    ask_for_postprint,
    ask_for_width,
    ask_which_line_to_edit,
    ask_which_line_to_scale,
    back_to_main_menu,
    back_to_menu_callback,
    cancel,
    generate_pdf_callback,
    generate_preview,
    last_order_command,
    save_color,
    save_edited_text,
    save_font,
    save_height,
    save_line_count_and_ask_text,
    save_postprint,
    save_scale,
    save_text_and_continue,    save_width,
    start,
    stats_command,
)
from .config import (
    AWAIT_BG_COLOR,
    AWAIT_FONT_CHOICE,
    AWAIT_HEIGHT,
    AWAIT_LINE_CHOICE_FOR_EDIT,
    AWAIT_LINE_COUNT,
    AWAIT_LINE_FOR_SCALE,
    AWAIT_NEW_TEXT,
    AWAIT_PERCENTAGE,
    AWAIT_POSTPRINT,
    AWAIT_TEXT_LINES,
    AWAIT_WIDTH,
    BTN_BG_COLOR,
    BTN_BACK,
    BTN_CANCEL,
    BTN_EDIT_TEXT,
    BTN_FONT,
    BTN_GENERATE,
    BTN_HEIGHT,
    BTN_POSTPRINT,
    BTN_RESTART,
    BTN_SCALE_TEXT,
    BTN_TEXT_COLOR,
    BTN_TEXT_LINES,
    BTN_WIDTH,
    MAIN_MENU,
    PREVIEW_CONFIRM,
    TELEGRAM_BOT_TOKEN,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Путь к файлу персистентности внутри контейнера
# Volume смонтирован как ./bot_data:/app/data в docker-compose.yml
PERSISTENCE_FILE = "/app/data/bot_persistence.pickle"


def main() -> None:
    persistence = PicklePersistence(filepath=PERSISTENCE_FILE)

    application = (
        Application.builder()        .token(TELEGRAM_BOT_TOKEN)
        .persistence(persistence)
        .build()
    )

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            MessageHandler(Regex(f"^{BTN_RESTART}$"), start),
        ],
        states={
            MAIN_MENU: [
                MessageHandler(Regex(f"^{BTN_WIDTH}$"),      ask_for_width),
                MessageHandler(Regex(f"^{BTN_HEIGHT}$"),     ask_for_height),
                MessageHandler(Regex(f"^{BTN_BG_COLOR}$"),   ask_for_color),
                MessageHandler(Regex(f"^{BTN_TEXT_COLOR}$"), ask_for_color),
                MessageHandler(Regex(f"^{BTN_FONT}$"),       ask_for_font),
                MessageHandler(Regex(f"^{BTN_TEXT_LINES}$"), ask_for_line_count),
                MessageHandler(Regex(f"^{BTN_POSTPRINT}$"),  ask_for_postprint),
                MessageHandler(Regex(f"^{BTN_EDIT_TEXT}$"),  ask_which_line_to_edit),
                MessageHandler(Regex(f"^{BTN_SCALE_TEXT}$"), ask_which_line_to_scale),
                MessageHandler(Regex(f"^{BTN_GENERATE}$"),   generate_preview),
            ],
            AWAIT_WIDTH: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_width),
            ],
            AWAIT_HEIGHT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_height),
            ],
            AWAIT_BG_COLOR: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_color),
            ],
            AWAIT_FONT_CHOICE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_font),
            ],
            AWAIT_LINE_COUNT: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    save_line_count_and_ask_text,
                ),
            ],
            AWAIT_TEXT_LINES: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    save_text_and_continue,
                ),
            ],
            AWAIT_POSTPRINT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_postprint),
            ],            AWAIT_LINE_CHOICE_FOR_EDIT: [
                MessageHandler(Regex(f"^{BTN_BACK}$"), back_to_main_menu),
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, ask_for_new_text
                ),
            ],
            AWAIT_NEW_TEXT: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, save_edited_text
                ),
            ],
            AWAIT_LINE_FOR_SCALE: [
                MessageHandler(Regex(f"^{BTN_BACK}$"), back_to_main_menu),
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, ask_for_percentage
                ),
            ],
            AWAIT_PERCENTAGE: [
                MessageHandler(
                    Regex(f"^{BTN_BACK}$"), ask_which_line_to_scale
                ),
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_scale),
            ],
            PREVIEW_CONFIRM: [
                CallbackQueryHandler(
                    generate_pdf_callback, pattern="^generate_pdf$"
                ),
                CallbackQueryHandler(
                    back_to_menu_callback, pattern="^cancel_generation$"
                ),
                MessageHandler(
                    filters.SUCCESSFUL_PAYMENT, successful_payment_handler
                ),
            ],
        },
        fallbacks=[
            CommandHandler("start", start),
            MessageHandler(Regex(f"^{BTN_CANCEL}$"), cancel),
            CommandHandler("cancel", cancel),
        ],
        # Важно: name нужен для корректного восстановления из PicklePersistence
        name="banner_conversation",
        persistent=True,
        per_message=False,
    )

    application.add_handler(conv_handler)
    application.add_handler(PreCheckoutQueryHandler(pre_checkout_handler))
    # Обработчик успешного платежа оставлен снаружи conv_handler
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))    application.add_handler(CommandHandler("stats",     stats_command))
    application.add_handler(CommandHandler("lastorder", last_order_command))

    logger.info("Бот запущен.")
    application.run_polling(
        # drop_pending_updates=True сбрасывает накопившиеся апдейты
        # при рестарте — исключает "эхо" старых команд
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
