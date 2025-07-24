import logging
from telegram.ext import (Application, CommandHandler, MessageHandler, filters, ConversationHandler, CallbackQueryHandler)
from telegram.ext.filters import Regex
from .config import *
from .bot_handlers import *

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

def main() -> None:
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.bot.set_my_commands([('start', BTN_RESTART)])

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start), MessageHandler(Regex(f'^{BTN_RESTART}$'), start)],
        states={
            MAIN_MENU: [
                MessageHandler(Regex(f'^{BTN_WIDTH}$'), ask_for_width),
                MessageHandler(Regex(f'^{BTN_HEIGHT}$'), ask_for_height),
                MessageHandler(Regex(f'^{BTN_BG_COLOR}$'), ask_for_color),
                MessageHandler(Regex(f'^{BTN_TEXT_COLOR}$'), ask_for_color),
                MessageHandler(Regex(f'^{BTN_FONT}$'), ask_for_font),
                MessageHandler(Regex(f'^{BTN_TEXT_LINES}$'), ask_for_line_count),
                MessageHandler(Regex(f'^{BTN_POSTPRINT}$'), ask_for_postprint),
                MessageHandler(Regex(f'^{BTN_EDIT_TEXT}$'), ask_which_line_to_edit),
                # --- ИЗМЕНЕНИЕ: Новый обработчик ---
                MessageHandler(Regex(f'^{BTN_SCALE_TEXT}$'), ask_which_line_to_scale),
                MessageHandler(Regex(f'^{BTN_GENERATE}$'), generate_preview),
            ],
            # --- ИЗМЕНЕНИЕ: Новые состояния ---
            AWAIT_LINE_FOR_SCALE: [
                MessageHandler(Regex(f'^{BTN_BACK}$'), back_to_main_menu),
                MessageHandler(filters.TEXT & ~filters.COMMAND, ask_for_percentage)
            ],
            AWAIT_PERCENTAGE: [
                MessageHandler(Regex(f'^{BTN_BACK}$'), ask_which_line_to_scale),
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_scale)
            ],
            # --- (остальные состояния без изменений) ---
            AWAIT_LINE_CHOICE_FOR_EDIT: [MessageHandler(Regex(f'^{BTN_BACK}$'), back_to_main_menu), MessageHandler(filters.TEXT & ~filters.COMMAND, ask_for_new_text)],
            AWAIT_NEW_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_edited_text)],
            AWAIT_WIDTH: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_width)],
            AWAIT_HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_height)],
            AWAIT_BG_COLOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_color)],
            AWAIT_FONT_CHOICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_font)],
            AWAIT_LINE_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_line_count_and_ask_text)],
            AWAIT_TEXT_LINES: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_text_and_continue)],
            AWAIT_POSTPRINT: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_postprint)],
            PREVIEW_CONFIRM: [CallbackQueryHandler(generate_pdf_callback, pattern="^generate_pdf$"), CallbackQueryHandler(back_to_menu_callback, pattern="^cancel_generation$")],
        },
        fallbacks=[CommandHandler("start", start), MessageHandler(Regex(f'^{BTN_CANCEL}$'), cancel), CommandHandler("cancel", cancel)],
        per_message=False,
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("lastorder", last_order_command))
    
    application.run_polling()

if __name__ == "__main__":
    main()
