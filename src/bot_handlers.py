"""
bot_handlers.py
~~~~~~~~~~~~~~~
Обработчики команд и сообщений Telegram-бота.
FSM (ConversationHandler) управляет диалогом настройки баннера.
"""

import logging
import os
from functools import wraps

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.ext import ContextTypes, ConversationHandler

from .banner_generator import (
    create_final_pdf,
    create_font_preview_image,
    create_preview_jpeg,
)
from .config import (
    ADMIN_TELEGRAM_ID,
    BTN_BACK,
    BTN_BG_COLOR,
    BTN_CANCEL,
    BTN_EDIT_TEXT,
    BTN_FONT,
    BTN_GENERATE,
    BTN_HEIGHT,
    BTN_POSTPRINT,
    BTN_RESTART,
    BTN_SCALE_TEXT,
    BTN_TEXT_COLOR,
    BTN_TEXT_LINES,
    BTN_WIDTH,
    COLORS,
    FONTS,
    MAIN_MENU,
    MAX_DIMENSION,
    MIN_DIMENSION,
    ORDERS_DIR,
    POSTPRINT_NONE,
    POSTPRINT_OPTIONS,
    TELEGRAM_CHANNEL_ID,
    AWAIT_BG_COLOR,
    AWAIT_FONT_CHOICE,
    AWAIT_HEIGHT,
    AWAIT_LINE_CHOICE_FOR_EDIT,
    AWAIT_LINE_COUNT,
    AWAIT_LINE_FOR_SCALE,
    AWAIT_NEW_TEXT,
    AWAIT_PERCENTAGE,
    AWAIT_POSTPRINT,
    AWAIT_TEXT_LINES,
    AWAIT_WIDTH,
    PREVIEW_CONFIRM,
)
from .order_manager import get_next_order_number, get_stats
from .payment_handlers import send_pdf_invoice
from .user_db import init_db, upsert_user

logger = logging.getLogger(__name__)


def admin_only(func):
    @wraps(func)
    async def wrapped(
        update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs
    ):
        if str(update.effective_user.id) != ADMIN_TELEGRAM_ID:
            await update.message.reply_text("У вас нет прав для этой команды.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapped


def _config_complete(config: dict) -> bool:
    required = [
        "width", "height", "bg_color", "text_color",
        "font", "text_lines", "postprint",
    ]
    return all(k in config and config[k] for k in required)


def _colors_conflict(config: dict) -> bool:
    """Возвращает True если цвет фона и цвет текста совпадают."""
    return (
        config.get("bg_color")
        and config.get("text_color")
        and config["bg_color"] == config["text_color"]
    )


async def display_menu(message, context: ContextTypes.DEFAULT_TYPE) -> None:
    config = context.user_data.get("config", {})
    lines = ["<b>Текущие настройки баннера:</b>"]

    def row(icon, label, value):
        return f"{icon} {label}: {value}"

    params = [
        (BTN_WIDTH,      config.get("width")),
        (BTN_HEIGHT,     config.get("height")),
        (BTN_BG_COLOR,   config.get("bg_color")),
        (BTN_TEXT_COLOR, config.get("text_color")),
        (BTN_FONT,       config.get("font")),
    ]
    for label, val in params:
        if val:
            lines.append(row("🟢", label, val))
        else:
            lines.append(row("🔴", label, "не задан"))

    text_items = config.get("text_lines")
    if text_items:
        parts = [
            f"«{item['text']}» ({int(item.get('scale', 1.0) * 100)}%)"
            for item in text_items
        ]
        lines.append(
            f"🟢 {BTN_TEXT_LINES}:\n  — " + "\n  — ".join(parts)
        )
    else:
        lines.append(f"🔴 {BTN_TEXT_LINES}: не задан")

    postprint = config.get("postprint")
    if postprint:
        lines.append(row("🟢", BTN_POSTPRINT, postprint))
    else:
        lines.append(row("🔴", BTN_POSTPRINT, "не задана"))

    buttons = [
        [BTN_WIDTH, BTN_HEIGHT],
        [BTN_BG_COLOR, BTN_TEXT_COLOR],
        [BTN_FONT, BTN_POSTPRINT],
    ]
    text_row = [BTN_TEXT_LINES]
    if text_items:
        text_row += [BTN_EDIT_TEXT, BTN_SCALE_TEXT]
    buttons.append(text_row)
    buttons.append([BTN_GENERATE])
    buttons.append([BTN_CANCEL])

    keyboard = ReplyKeyboardMarkup(buttons, resize_keyboard=True)
    await message.reply_text(
        "\n".join(lines), reply_markup=keyboard, parse_mode="HTML"
    )
    if _colors_conflict(config):
        await message.reply_text(
            "⚠️ Цвет фона и текста совпадают — измените один из них."
        )


@admin_only
async def stats_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    await update.message.reply_text(get_stats(), parse_mode="MarkdownV2")


@admin_only
async def last_order_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    last_order_path = context.bot_data.get("last_order_path")
    if last_order_path and os.path.exists(last_order_path):
        filename = os.path.basename(last_order_path)
        await update.message.reply_document(
            document=open(last_order_path, "rb"),
            caption=f"Последний заказ: `{filename}`",
            parse_mode="MarkdownV2",
        )
    else:
        await update.message.reply_text(
            "Заказов с последнего перезапуска ещё не было."
        )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["config"] = {"postprint": POSTPRINT_NONE}
    await update.message.reply_text(
        "Привет! Давайте создадим ваш баннер.\n"
        "Используйте кнопки ниже для настройки."
    )
    await display_menu(update.message, context)
    return MAIN_MENU


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Действие отменено.",
        reply_markup=ReplyKeyboardMarkup(
            [[BTN_RESTART]], resize_keyboard=True, one_time_keyboard=True
        ),
    )
    context.user_data.clear()
    return ConversationHandler.END


async def back_to_main_menu(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    await display_menu(update.message, context)
    return MAIN_MENU


async def ask_for_width(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    await update.message.reply_text(
        f"Введите ширину в мм (от {MIN_DIMENSION} до {MAX_DIMENSION}):",
        reply_markup=ReplyKeyboardRemove(),
    )
    return AWAIT_WIDTH


async def save_width(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    try:
        value = int(update.message.text)
        if not (MIN_DIMENSION <= value <= MAX_DIMENSION):
            raise ValueError
        context.user_data["config"]["width"] = value
    except (ValueError, TypeError):
        await update.message.reply_text(
            f"Введите целое число от {MIN_DIMENSION} до {MAX_DIMENSION}."
        )
    await display_menu(update.message, context)
    return MAIN_MENU


async def ask_for_height(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    await update.message.reply_text(
        f"Введите высоту в мм (от {MIN_DIMENSION} до {MAX_DIMENSION}):",
        reply_markup=ReplyKeyboardRemove(),
    )
    return AWAIT_HEIGHT


async def save_height(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    try:
        value = int(update.message.text)
        if not (MIN_DIMENSION <= value <= MAX_DIMENSION):
            raise ValueError
        context.user_data["config"]["height"] = value
    except (ValueError, TypeError):
        await update.message.reply_text(
            f"Введите целое число от {MIN_DIMENSION} до {MAX_DIMENSION}."
        )
    await display_menu(update.message, context)
    return MAIN_MENU


async def ask_for_color(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    context.user_data["color_target"] = update.message.text
    color_buttons = [
        f"{details['emoji']} {name}" for name, details in COLORS.items()
    ]
    keyboard = [
        color_buttons[i:i + 2] for i in range(0, len(color_buttons), 2)
    ]
    await update.message.reply_text(
        "Выберите цвет:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
    )
    return AWAIT_BG_COLOR


async def save_color(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    try:
        color_name = update.message.text.split(" ", 1)[1]
        if color_name not in COLORS:
            raise ValueError
        target = context.user_data.get("color_target")
        if target == BTN_BG_COLOR:
            context.user_data["config"]["bg_color"] = color_name
        elif target == BTN_TEXT_COLOR:
            context.user_data["config"]["text_color"] = color_name
    except (ValueError, IndexError):
        await update.message.reply_text(
            "Пожалуйста, нажмите на кнопку с цветом."
        )
        await display_menu(update.message, context)
        return MAIN_MENU

    await display_menu(update.message, context)
    return MAIN_MENU


async def ask_for_font(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    await update.message.reply_text(
        "Готовлю превью шрифтов...", reply_markup=ReplyKeyboardRemove()
    )
    preview = create_font_preview_image()
    await update.message.reply_photo(
        photo=preview, caption="Доступные шрифты:"
    )
    font_names = list(FONTS.keys())
    keyboard = [font_names[i:i + 2] for i in range(0, len(font_names), 2)]
    await update.message.reply_text(
        "Выберите шрифт:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
    )
    return AWAIT_FONT_CHOICE


async def save_font(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    if update.message.text in FONTS:
        context.user_data["config"]["font"] = update.message.text
    else:
        await update.message.reply_text("Выберите шрифт из списка.")
    await display_menu(update.message, context)
    return MAIN_MENU


async def ask_for_line_count(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    context.user_data["config"]["text_lines"] = []
    await update.message.reply_text(
        "Сколько строк текста будет на баннере?",
        reply_markup=ReplyKeyboardMarkup(
            [["1", "2"], ["3", "4"]], resize_keyboard=True
        ),
    )
    return AWAIT_LINE_COUNT


async def save_line_count_and_ask_text(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    try:
        count = int(update.message.text)
        if not 1 <= count <= 4:
            raise ValueError
        context.user_data["config"]["line_count"] = count
        await update.message.reply_text(
            "Введите текст для строки 1:",
            reply_markup=ReplyKeyboardRemove(),
        )
        return AWAIT_TEXT_LINES
    except (ValueError, TypeError):
        await update.message.reply_text("Выберите число от 1 до 4.")
        await display_menu(update.message, context)
        return MAIN_MENU


async def save_text_and_continue(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    config = context.user_data["config"]
    config.setdefault("text_lines", []).append(
        {"text": update.message.text, "scale": 1.0}
    )
    if len(config["text_lines"]) < config.get("line_count", 0):
        next_num = len(config["text_lines"]) + 1
        await update.message.reply_text(
            f"Принято. Введите текст для строки {next_num}:"
        )
        return AWAIT_TEXT_LINES
    else:
        await update.message.reply_text("Весь текст сохранён!")
        await display_menu(update.message, context)
        return MAIN_MENU


async def ask_which_line_to_edit(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    items = context.user_data.get("config", {}).get("text_lines", [])
    buttons = [
        [f"Строка {i + 1}: «{item['text'][:20]}»"]
        for i, item in enumerate(items)
    ] + [[BTN_BACK]]
    await update.message.reply_text(
        "Какую строку изменить?",
        reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True),
    )
    return AWAIT_LINE_CHOICE_FOR_EDIT


async def ask_for_new_text(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    try:
        line_index = (
            int(update.message.text.split(":")[0].split(" ")[1]) - 1
        )
        context.user_data["edit_line_index"] = line_index
        await update.message.reply_text(
            f"Введите новый текст для строки {line_index + 1}:",
            reply_markup=ReplyKeyboardRemove(),
        )
        return AWAIT_NEW_TEXT
    except (ValueError, IndexError):
        return AWAIT_LINE_CHOICE_FOR_EDIT


async def save_edited_text(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    idx = context.user_data.pop("edit_line_index", None)
    if idx is not None:
        context.user_data["config"]["text_lines"][idx]["text"] = (
            update.message.text
        )
    await display_menu(update.message, context)
    return MAIN_MENU


async def ask_which_line_to_scale(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    items = context.user_data.get("config", {}).get("text_lines", [])
    buttons = [
        [f"Строка {i + 1} ({int(item.get('scale', 1.0) * 100)}%)"]
        for i, item in enumerate(items)
    ] + [[BTN_BACK]]
    await update.message.reply_text(
        "Выберите строку для изменения масштаба:",
        reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True),
    )
    return AWAIT_LINE_FOR_SCALE


async def ask_for_percentage(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    try:
        line_index = int(update.message.text.split(" ")[1]) - 1
        context.user_data["scale_line_index"] = line_index
        buttons = [
            ["100%", "90%"],
            ["80%", "70%"],
            ["60%", "50%"],
            [BTN_BACK],
        ]
        await update.message.reply_text(
            f"Выберите масштаб для строки {line_index + 1}:",
            reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True),
        )
        return AWAIT_PERCENTAGE
    except (ValueError, IndexError):
        return AWAIT_LINE_FOR_SCALE


async def save_scale(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    try:
        idx = context.user_data.pop("scale_line_index")
        scale_value = int(update.message.text.replace("%", "")) / 100.0
        if not (0.1 <= scale_value <= 1.0):
            raise ValueError
        context.user_data["config"]["text_lines"][idx]["scale"] = scale_value
    except (KeyError, IndexError, ValueError):
        await update.message.reply_text(
            "Выберите масштаб из предложенных кнопок."
        )
    await display_menu(update.message, context)
    return MAIN_MENU


async def ask_for_postprint(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    keyboard = [[key] for key in POSTPRINT_OPTIONS.keys()]
    await update.message.reply_text(
        "Выберите постпечатную обработку:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
    )
    return AWAIT_POSTPRINT


async def save_postprint(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    if update.message.text in POSTPRINT_OPTIONS:
        context.user_data["config"]["postprint"] = update.message.text
    else:
        await update.message.reply_text("Выберите вариант из списка.")
    await display_menu(update.message, context)
    return MAIN_MENU


async def generate_preview(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    config = context.user_data.get("config", {})
    if not _config_complete(config):
        await update.message.reply_text(
            "Пожалуйста, заполните все параметры (отмечены красным).",
        )
        await display_menu(update.message, context)
        return MAIN_MENU

    if _colors_conflict(config):
        await update.message.reply_text(
            "⚠️ Цвет фона и цвет текста совпадают — измените один из них."
        )
        await display_menu(update.message, context)
        return MAIN_MENU

    await update.message.reply_text(
        "Создаю превью...", reply_markup=ReplyKeyboardRemove()
    )
    try:
        preview = create_preview_jpeg(config)
    except Exception as exc:
        logger.exception("Ошибка генерации превью")
        await update.message.reply_text(f"Ошибка генерации превью: {exc}")
        await display_menu(update.message, context)
        return MAIN_MENU

    await update.message.reply_photo(
        photo=preview,
        caption="Всё верно?",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "Сгенерировать PDF",
                    callback_data="generate_pdf",
                ),
                InlineKeyboardButton(
                    "Назад",
                    callback_data="cancel_generation",
                ),
            ]
        ]),
    )
    return PREVIEW_CONFIRM


async def generate_pdf_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Paywall-версия. Вместо немедленной генерации PDF:
      1. Генерирует номер заказа и сохраняет параметры в user_data.
      2. Отправляет Stars-инвойс через send_pdf_invoice.
    Сама генерация PDF происходит в successful_payment_handler после оплаты.
    """
    query = update.callback_query
    await query.answer()

    config = context.user_data["config"]
    user = update.effective_user

    # Регистрируем/обновляем пользователя в БД
    upsert_user(
        tg_id=user.id,
        username=user.username,
        first_name=user.first_name,
    )

    order_number = get_next_order_number()
    postprint_code = POSTPRINT_OPTIONS.get(config["postprint"], "XX")

    # Сохраняем всё необходимое для генерации PDF после оплаты
    context.user_data["pending_pdf_order"] = {
        "order_number": order_number,
        "postprint_code": postprint_code,
        "config": config,
    }

    await query.edit_message_caption(
        caption=(
            f"Заказ #{order_number} готов к оплате.\n"
            "После оплаты вы сразу получите PDF для типографии."
        )
    )

    await send_pdf_invoice(update, context, order_number)
    return PREVIEW_CONFIRM


async def back_to_menu_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    query = update.callback_query
    await query.answer()
    await query.delete_message()
    await display_menu(update.effective_message, context)
    return MAIN_MENU
