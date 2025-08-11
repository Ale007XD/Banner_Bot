import logging
import asyncio
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, ConversationHandler, CallbackQueryHandler
)
from telegram.ext.filters import Regex
from .config import *
from .bot_handlers import (
    start, ask_which_line_to_scale, ask_for_percentage, save_scale,
    back_to_main_menu, ask_for_postprint, save_postprint,
    generate_preview, generate_pdf_callback, back_to_menu_callback
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

async def main() -> None:
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    await application.bot.set_my_commands([('start', BTN_RESTART)])
    
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start), 
            MessageHandler(Regex(f'^{BTN_RESTART}$'), start)
        ],
        states={
            MAIN_MENU: [
                MessageHandler(Regex(f'^{BTN_SCALE_TEXT}$'), ask_which_line_to_scale),
                MessageHandler(Regex(f'^{BTN_POSTPRINT}$'), ask_for_postprint),
                MessageHandler(Regex(f'^{BTN_GENERATE}$'), generate_preview),
            ],
            AWAIT_LINE_FOR_SCALE: [
                MessageHandler(Regex(f'^{BTN_BACK}$'), back_to_main_menu),
                MessageHandler(filters.TEXT & ~filters.COMMAND, ask_for_percentage)
            ],
            AWAIT_PERCENTAGE: [
                MessageHandler(Regex(f'^{BTN_BACK}$'), ask_which_line_to_scale),
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_scale)
            ],
            AWAIT_POSTPRINT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_postprint)
            ],
            PREVIEW_CONFIRM: [
                CallbackQueryHandler(generate_pdf_callback, pattern="^generate_pdf$"), 
                CallbackQueryHandler(back_to_menu_callback, pattern="^back_to_menu$")
            ],
        },
        fallbacks=[
            CommandHandler("start", start)
        ],
        per_message=False,
    )
    
    application.add_handler(conv_handler)
    
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    await application.updater.idle()

if __name__ == "__main__":
    asyncio.run(main())
