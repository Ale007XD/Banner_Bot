import logging
import asyncio
import re
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, ConversationHandler, CallbackQueryHandler
)
from telegram.ext.filters import Regex
from .config import *
from .bot_handlers import (
    start, ask_which_line_to_scale, ask_for_percentage, save_scale, 
    back_to_main_menu, ask_for_postprint, save_postprint, generate_preview, 
    generate_pdf_callback, back_to_menu_callback, show_stats
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)

async def main() -> None:
    """Main function to set up and run the bot with PTB v21 compatibility."""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Set bot commands for better UX
    await application.bot.set_my_commands([('start', BTN_RESTART)])
    
    # Simplified conversation handler with only existing handlers
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start), 
            MessageHandler(Regex(f'^{re.escape(BTN_RESTART)}$'), start)
        ],
        states={
            # Main menu - only with existing handlers
            MAIN_MENU: [
                MessageHandler(Regex(f'^{re.escape(BTN_SCALE_TEXT)}$'), ask_which_line_to_scale),
                MessageHandler(Regex(f'^{re.escape(BTN_POSTPRINT)}$'), ask_for_postprint),
                MessageHandler(Regex(f'^{re.escape(BTN_GENERATE)}$'), generate_preview),
                MessageHandler(Regex(f'^{re.escape(BTN_STATS)}$'), show_stats),
            ],
            
            # Scale text - line selection
            AWAIT_LINE_FOR_SCALE: [
                MessageHandler(Regex(f'^{re.escape(BTN_BACK)}$'), back_to_main_menu),
                MessageHandler(Regex(f'^{re.escape(BTN_CANCEL)}$'), start),
                MessageHandler(filters.TEXT & ~filters.COMMAND, ask_for_percentage)
            ],
            
            # Scale text - percentage input
            AWAIT_PERCENTAGE: [
                MessageHandler(Regex(f'^{re.escape(BTN_BACK)}$'), ask_which_line_to_scale),
                MessageHandler(Regex(f'^{re.escape(BTN_CANCEL)}$'), start),
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_scale)
            ],
            
            # Postprint selection
            AWAIT_POSTPRINT: [
                MessageHandler(Regex(f'^{re.escape(BTN_BACK)}$'), back_to_main_menu),
                MessageHandler(Regex(f'^{re.escape(BTN_CANCEL)}$'), start),
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_postprint)
            ],
            
            # Preview confirmation with callback queries
            PREVIEW_CONFIRM: [
                CallbackQueryHandler(generate_pdf_callback, pattern=r"^generate_pdf$"), 
                CallbackQueryHandler(back_to_menu_callback, pattern=r"^back_to_menu$")
            ],
        },
        fallbacks=[
            CommandHandler("start", start),
            MessageHandler(Regex(f'^{re.escape(BTN_RESTART)}$'), start)
        ],
        per_message=False,  # PTB v21 safe
    )
    
    # Add conversation handler to application
    application.add_handler(conv_handler)
    
    # PTB v21 compatible startup sequence
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    await application.updater.idle()

if __name__ == "__main__":
    asyncio.run(main())
