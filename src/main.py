import logging
from telegram.ext import Application, PicklePersistence, CommandHandler, ConversationHandler, MessageHandler, filters
# Импортируем именно то, что нужно из config.py
from .config import TELEGRAM_BOT_TOKEN, ADMIN_TELEGRAM_ID
# Импортируйте ваши хендлеры (предположим, они в bot_handlers.py)
from .bot_handlers import start, cancel, stats_command, last_order_command

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main() -> None:
    # Путь к файлу персистентности (убедитесь, что /app/data существует)
    persistence = PicklePersistence(filepath="/app/data/bot_persistence.pickle")

    # Инициализация приложения
    application = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN) # Ошибка NameError исчезнет
        .persistence(persistence)
        .build()
    )

    # Добавление хендлеров (пример структуры)
    # application.add_handler(...)

    logger.info("Бот запущен и готов к работе.")
    application.run_polling()

if __name__ == "__main__":
    main()
    
