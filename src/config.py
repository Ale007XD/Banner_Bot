import os
# Telegram settings
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHANNEL_ID = os.getenv('TELEGRAM_CHANNEL_ID', '')
# Параметры для баннера
SAFE_ZONE_MM = 30
MIN_DIMENSION = 500
MAX_DIMENSION = 3000
# Постпечатная обработка
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
# Кнопки интерфейса
BTN_WIDTH = "📏 Ширина"
BTN_HEIGHT = "📐 Высота"
BTN_BG_COLOR = "🎨 Цвет фона"
BTN_TEXT_COLOR = "✏️ Цвет текста"
BTN_FONT = "🔤 Шрифт"
BTN_TEXT_LINES = "📝 Количество строк"
BTN_EDIT_TEXT = "✏️ Редактировать текст"
BTN_POSTPRINT = "🔩 Постпечать"
BTN_PREVIEW = "👁 Предпросмотр"
BTN_SCALE_TEXT = "↔️ Масштаб строк"
BTN_STATS = "📊 Статистика"
BTN_RESTART = "🚀 Создать новый баннер"
BTN_GENERATE = "🚀 Сгенерировать баннер"
BTN_BACK = "⬅️ Назад"
BTN_CANCEL = "❌ Отмена"
# Состояния ConversationHandler
MAIN_MENU = 0
AWAIT_WIDTH = 1
AWAIT_HEIGHT = 2
AWAIT_BG_COLOR = 3
AWAIT_TEXT_COLOR = 4
AWAIT_FONT = 5
AWAIT_LINE_COUNT = 6
AWAIT_TEXT = 7
AWAIT_WHICH_LINE = 8
AWAIT_NEW_TEXT = 9
AWAIT_POSTPRINT = 10
AWAIT_LINE_FOR_SCALE = 11
AWAIT_PERCENTAGE = 12
# Callback данные для inline кнопок
CALLBACK_BACK_TO_MENU = "back_to_menu"
CALLBACK_GENERATE_PDF = "generate_pdf"
