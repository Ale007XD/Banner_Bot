import logging
import asyncio
import re
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, ConversationHandler, CallbackQueryHandler
)
from telegram.ext.filters import Regex
from .config import *
from .bot_handlers import (
    start, ask_width, ask_height, ask_bg_color, ask_line_count,
    ask_text_lines, ask_text_color, ask_font_choice, ask_which_line_to_scale,
    ask_for_percentage, save_scale, back_to_main_menu, ask_for_postprint,
    save_postprint, generate_preview, generate_pdf_callback, back_to_menu_callback,
    ask_line_choice_for_edit, ask_new_text, save_width, save_height,
    save_bg_color, save_line_count, save_text_lines, save_text_color,
    save_font_choice, save_new_text, back_to_text_menu
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

async def main() -> None:
    """Main function to set up and run the bot with PTB v21 compatibility."""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Set bot commands for better UX
    await application.bot.set_my_commands([('start', BTN_RESTART)])
    
    # Complete conversation handler with all states and strict pattern matching
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start), 
            MessageHandler(Regex(f'^{re.escape(BTN_RESTART)}$'), start)
        ],
        states={
            # Main menu - all primary bot functions
            MAIN_MENU: [
                MessageHandler(Regex(f'^{re.escape(BTN_WIDTH)}$'), ask_width),
                MessageHandler(Regex(f'^{re.escape(BTN_HEIGHT)}$'), ask_height),
                MessageHandler(Regex(f'^{re.escape(BTN_BG_COLOR)}$'), ask_bg_color),
                MessageHandler(Regex(f'^{re.escape(BTN_LINE_COUNT)}$'), ask_line_count),
                MessageHandler(Regex(f'^{re.escape(BTN_TEXT_LINES)}$'), ask_text_lines),
                MessageHandler(Regex(f'^{re.escape(BTN_TEXT_COLOR)}$'), ask_text_color),
                MessageHandler(Regex(f'^{re.escape(BTN_FONT)}$'), ask_font_choice),
                MessageHandler(Regex(f'^{re.escape(BTN_SCALE_TEXT)}$'), ask_which_line_to_scale),
                MessageHandler(Regex(f'^{re.escape(BTN_POSTPRINT)}$'), ask_for_postprint),
                MessageHandler(Regex(f'^{re.escape(BTN_EDIT_TEXT)}$'), ask_line_choice_for_edit),
                MessageHandler(Regex(f'^{re.escape(BTN_GENERATE)}$'), generate_preview),
            ],
            
            # Width input state
            AWAIT_WIDTH: [
                MessageHandler(Regex(f'^{re.escape(BTN_BACK)}$'), back_to_main_menu),
                MessageHandler(Regex(f'^{re.escape(BTN_CANCEL)}$'), start),
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_width)
            ],
            
            # Height input state  
            AWAIT_HEIGHT: [
                MessageHandler(Regex(f'^{re.escape(BTN_BACK)}$'), back_to_main_menu),
                MessageHandler(Regex(f'^{re.escape(BTN_CANCEL)}$'), start),
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_height)
            ],
            
            # Background color selection
            AWAIT_BG_COLOR: [
                MessageHandler(Regex(f'^{re.escape(BTN_BACK)}$'), back_to_main_menu),
                MessageHandler(Regex(f'^{re.escape(BTN_CANCEL)}$'), start),
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_bg_color)
            ],
            
            # Line count input
            AWAIT_LINE_COUNT: [
                MessageHandler(Regex(f'^{re.escape(BTN_BACK)}$'), back_to_main_menu),
                MessageHandler(Regex(f'^{re.escape(BTN_CANCEL)}$'), start),
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_line_count)
            ],
            
            # Text lines input
            AWAIT_TEXT_LINES: [
                MessageHandler(Regex(f'^{re.escape(BTN_BACK)}$'), back_to_main_menu),
                MessageHandler(Regex(f'^{re.escape(BTN_CANCEL)}$'), start),
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_text_lines)
            ],
            
            # Text color selection
            AWAIT_TEXT_COLOR: [
                MessageHandler(Regex(f'^{re.escape(BTN_BACK)}$'), back_to_main_menu),
                MessageHandler(Regex(f'^{re.escape(BTN_CANCEL)}$'), start),
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_text_color)
            ],
            
            # Font choice selection
            AWAIT_FONT_CHOICE: [
                MessageHandler(Regex(f'^{re.escape(BTN_BACK)}$'), back_to_main_menu),
                MessageHandler(Regex(f'^{re.escape(BTN_CANCEL)}$'), start),
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_font_choice)
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
            
            # Edit text - line choice
            AWAIT_LINE_CHOICE_FOR_EDIT: [
                MessageHandler(Regex(f'^{re.escape(BTN_BACK)}$'), back_to_main_menu),
                MessageHandler(Regex(f'^{re.escape(BTN_CANCEL)}$'), start),
                MessageHandler(filters.TEXT & ~filters.COMMAND, ask_new_text)
            ],
            
            # Edit text - new text input
            AWAIT_NEW_TEXT: [
                MessageHandler(Regex(f'^{re.escape(BTN_BACK)}$'), back_to_text_menu),
                MessageHandler(Regex(f'^{re.escape(BTN_CANCEL)}$'), start),
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_new_text)
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
