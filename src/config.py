import os
from dotenv import load_dotenv

# Загружаем переменные из .env файла
load_dotenv()

# Токен для доступа к Telegram Bot API
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# ID канала, куда будут отправляться готовые баннеры
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")

if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHANNEL_ID:
    raise ValueError(
        "Необходимо задать переменные окружения TELEGRAM_BOT_TOKEN и TELEGRAM_CHANNEL_ID в файле .env"
    )

# Константы для диалога
(WIDTH, HEIGHT, BG_COLOR, LINE_COUNT, TEXT_LINES, TEXT_COLOR, FONT_CHOICE, PREVIEW_CONFIRM) = range(8)

# Параметры для баннера
SAFE_ZONE_MM = 30
MIN_DIMENSION = 500
MAX_DIMENSION = 3000

# Названия шрифтов и соответствующие файлы
FONTS = {
    "Golos Text": "fonts/GolosText-Regular.ttf",
    "Tenor Sans": "fonts/TenorSans-Regular.ttf",
    "Fira Sans": "fonts/FiraSans-Regular.ttf",
    "Igra Sans": "fonts/IgraSans-Regular.ttf",
}

# Названия цветов и их значения
COLORS = {
    "Белый": {
        "cmyk": (0, 0, 0, 0),
        "rgb": (255, 255, 255)
    },
    "Черный": {
        "cmyk": (0, 0, 0, 100),
        "rgb": (0, 0, 0)
    },
    "Красный": {
        "cmyk": (0, 100, 100, 0),
        "rgb": (255, 0, 0)
    },
    "Желтый": {
        "cmyk": (0, 0, 100, 0),
        "rgb": (255, 255, 0)
    },
    "Синий": {
        "cmyk": (100, 100, 0, 0),
        "rgb": (0, 0, 255)
    },
    "Зеленый": {
        "cmyk": (100, 0, 100, 0),
        "rgb": (0, 128, 0)
    },
}
