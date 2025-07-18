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

# Добавляем новое состояние в конец
(MAIN_MENU, AWAIT_WIDTH, AWAIT_HEIGHT, AWAIT_BG_COLOR, 
 AWAIT_LINE_COUNT, AWAIT_TEXT_LINES, AWAIT_TEXT_COLOR, 
 AWAIT_FONT_CHOICE, PREVIEW_CONFIRM, AWAIT_POSTPRINT) = range(10) # <-- Увеличили range до 10

# Тексты для кнопок, чтобы избежать "магических строк" в коде
BTN_WIDTH = "📏 Ширина"
BTN_HEIGHT = "📏 Высота"
BTN_BG_COLOR = "🎨 Цвет фона"
BTN_LINE_COUNT = "🔠 Кол-во строк"
BTN_TEXT_LINES = "✍️ Текст"
BTN_TEXT_COLOR = "🎨 Цвет текста"
BTN_FONT = "✒️ Шрифт"
BTN_GENERATE = "🚀 Сгенерировать баннер"
BTN_CANCEL = "❌ Отмена"
BTN_POSTPRINT = "🔩 Постпечать"

# Параметры для баннера
SAFE_ZONE_MM = 30
MIN_DIMENSION = 500
MAX_DIMENSION = 3000

POSTPRINT_NONE = "Без люверсов"
POSTPRINT_CORNERS = "4 по углам"
POSTPRINT_PERIMETER = "Через 0.25м"

POSTPRINT_OPTIONS = {
    POSTPRINT_NONE: "NL",      # No Lugs
    POSTPRINT_CORNERS: "4L",   # 4 Lugs
    POSTPRINT_PERIMETER: "PL", # Perimeter Lugs
}

# Названия шрифтов и соответствующие файлы
FONTS = {
    "Golos Text": "fonts/GolosText-Regular.ttf",
    "Tenor Sans": "fonts/TenorSans-Regular.ttf",
    "Fira Sans": "fonts/FiraSans-Regular.ttf",
    "Igra Sans": "fonts/IgraSans-Regular.ttf",
}

# Названия цветов и их значения
# src/config.py

COLORS = {
    "Белый": {
        "cmyk": (0, 0, 0, 0),
        "rgb": (255, 255, 255),
        "emoji": "⚪️"
    },
    "Черный": {
        "cmyk": (0, 0, 0, 100),
        "rgb": (0, 0, 0),
        "emoji": "⚫️"
    },
    "Красный": {
        "cmyk": (0, 100, 100, 0),
        "rgb": (255, 0, 0),
        "emoji": "🔴"
    },
    "Желтый": {
        "cmyk": (0, 0, 100, 0),
        "rgb": (255, 255, 0),
        "emoji": "🟡"
    },
    "Синий": {
        "cmyk": (100, 100, 0, 0),
        "rgb": (0, 0, 255),
        "emoji": "🔵"
    },
    "Зеленый": {
        "cmyk": (100, 0, 100, 0),
        "rgb": (0, 128, 0),
        "emoji": "🟢"
    },
}

# Новая константа для кнопки перезапуска
BTN_RESTART = "🚀 Создать новый баннер"
