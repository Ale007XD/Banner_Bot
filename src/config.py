import os
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Telegram credentials
# ---------------------------------------------------------------------------
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")
ADMIN_TELEGRAM_ID = os.getenv("ADMIN_TELEGRAM_ID")

if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHANNEL_ID:
    raise ValueError(
        "Необходимо задать переменные окружения TELEGRAM_BOT_TOKEN "
        "и TELEGRAM_CHANNEL_ID в файле .env"
    )

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
# ICC-профиль для PDF/X (офсетная печать, стандарт типографий Европы/России)
ICC_PROFILE_PATH = os.getenv("ICC_PROFILE_PATH", "/profiles/ISOcoated_v2_300_eci.icc")

ORDERS_DIR = "orders"
COUNTER_FILE_PATH = "order_counter.json"

# ---------------------------------------------------------------------------
# Banner parameters
# ---------------------------------------------------------------------------
SAFE_ZONE_MM = 30       # Поля безопасности (отступ от края), мм
MIN_DIMENSION = 500     # Минимальный размер стороны баннера, мм
MAX_DIMENSION = 3000    # Максимальный размер стороны баннера, мм

# ---------------------------------------------------------------------------
# FSM states — диапазон 100+ чтобы не пересекаться с библиотечными
# ---------------------------------------------------------------------------
(
    MAIN_MENU,
    AWAIT_WIDTH,
    AWAIT_HEIGHT,
    AWAIT_BG_COLOR,
    AWAIT_LINE_COUNT,
    AWAIT_TEXT_LINES,
    AWAIT_TEXT_COLOR,
    AWAIT_FONT_CHOICE,
    PREVIEW_CONFIRM,
    AWAIT_POSTPRINT,
    AWAIT_LINE_CHOICE_FOR_EDIT,
    AWAIT_NEW_TEXT,
    AWAIT_LINE_FOR_SCALE,
    AWAIT_PERCENTAGE,
) = range(100, 114)

# ---------------------------------------------------------------------------
# Button labels — единственный источник истины, нет магических строк
# ---------------------------------------------------------------------------
BTN_WIDTH        = "📏 Ширина"
BTN_HEIGHT       = "📏 Высота"
BTN_BG_COLOR     = "🎨 Цвет фона"
BTN_TEXT_COLOR   = "🎨 Цвет текста"
BTN_FONT         = "✒️ Шрифт"
BTN_TEXT_LINES   = "✍️ Ввести текст"
BTN_EDIT_TEXT    = "✍️ Редактировать текст"
BTN_SCALE_TEXT   = "↔️ Масштаб строк"
BTN_POSTPRINT    = "🔩 Постпечать"
BTN_GENERATE     = "🚀 Сгенерировать баннер"
BTN_CANCEL       = "❌ Отмена"
BTN_BACK         = "↩️ Назад"
BTN_RESTART      = "🚀 Создать новый баннер"

# ---------------------------------------------------------------------------
# Post-print options
# ---------------------------------------------------------------------------
POSTPRINT_NONE      = "Без люверсов"
POSTPRINT_CORNERS   = "4 по углам"
POSTPRINT_PERIMETER = "Через 0.25м"

POSTPRINT_OPTIONS = {
    POSTPRINT_NONE:      "NL",   # No Lugs
    POSTPRINT_CORNERS:   "4L",   # 4 Lugs
    POSTPRINT_PERIMETER: "PL",   # Perimeter Lugs
}

# ---------------------------------------------------------------------------
# Fonts: display name → path inside container
# ---------------------------------------------------------------------------
FONTS = {
    "Golos Text": "fonts/GolosText-Regular.ttf",
    "Tenor Sans": "fonts/TenorSans-Regular.ttf",
    "Fira Sans":  "fonts/FiraSans-Regular.ttf",
    "Igra Sans":  "fonts/IgraSans-Regular.ttf",
}

# ---------------------------------------------------------------------------
# Colors: display name → RGB (preview) + CMYK (print, 0-100 scale)
# ---------------------------------------------------------------------------
COLORS = {
    "Белый": {
        "cmyk":  (0,   0,   0,   0),
        "rgb":   (255, 255, 255),
        "emoji": "⚪️",
    },
    "Черный": {
        "cmyk":  (0,   0,   0,   100),
        "rgb":   (0,   0,   0),
        "emoji": "⚫️",
    },
    "Красный": {
        "cmyk":  (0,   100, 100, 0),
        "rgb":   (255, 0,   0),
        "emoji": "🔴",
    },
    "Желтый": {
        "cmyk":  (0,   0,   100, 0),
        "rgb":   (255, 255, 0),
        "emoji": "🟡",
    },
    "Синий": {
        "cmyk":  (100, 100, 0,   0),
        "rgb":   (0,   0,   255),
        "emoji": "🔵",
    },
    "Зеленый": {
        "cmyk":  (100, 0,   100, 0),
        "rgb":   (0,   128, 0),
        "emoji": "🟢",
    },
}
