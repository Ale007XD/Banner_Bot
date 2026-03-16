import os
import logging
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    PicklePersistence, # Добавлено
    filters,
)
# ... ваши остальные импорты ...

def main() -> None:
    # Инициализируем сохранение данных в файл
    persistence = PicklePersistence(filepath="data/bot_persistence.pickle")

    application = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .persistence(persistence) # Подключаем к приложению
        .build()
    )

    conv_handler = ConversationHandler(
        name="banner_factory_v1", # Уникальное имя для базы данных pickle
        persistent=True,          # Включаем сохранение для этого диалога
        entry_points=[
            CommandHandler("start", start),
            MessageHandler(Regex(f"^{BTN_RESTART}$"), start),
        ],
        states={
            # ... все ваши состояния без изменений ...
        },
        fallbacks=[
            CommandHandler("start", start),
            MessageHandler(Regex(f"^{BTN_CANCEL}$"), cancel),
            CommandHandler("cancel", cancel),
        ],
        per_message=False,
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("lastorder", last_order_command))

    logger.info("Бот запущен с поддержкой Persistence.")
    application.run_polling()

if __name__ == "__main__":
    main()
    
