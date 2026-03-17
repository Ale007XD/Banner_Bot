"""
template_handlers.py
~~~~~~~~~~~~~~~~~~~~
Обработчики шаблонов для Banner Bot.

Три точки входа в воронке:
  1. Шаг размера      — инлайн-кнопки типовых форматов
  2. Шаг текста       — кнопка «💡 Примеры слоганов» → категории → вставка
  3. Шаг цвета        — кнопка «🎨 Готовые сочетания» → выбор → заполняет bg+text

Регистрация в ConversationHandler (main.py или bot_setup.py):
  - AWAIT_WIDTH:       добавить CallbackQueryHandler(tpl_size_chosen, pattern=r"^tpl_size:")
  - AWAIT_TEXT_LINES:  добавить CallbackQueryHandler(tpl_slogan_category, pattern=r"^tpl_scat:")
                       добавить CallbackQueryHandler(tpl_slogan_chosen, pattern=r"^tpl_slogan:")
                       добавить CallbackQueryHandler(tpl_slogan_cancel, pattern=r"^tpl_slogan_cancel$")
  - AWAIT_BG_COLOR:    добавить CallbackQueryHandler(tpl_color_chosen, pattern=r"^tpl_color:")
                       добавить CallbackQueryHandler(tpl_color_cancel, pattern=r"^tpl_color_cancel$")

Кнопка «💡 Примеры слоганов» добавляется в ask_for_line_count (bot_handlers.py).
Кнопка «🎨 Готовые сочетания» добавляется в ask_for_color (bot_handlers.py).
Инлайн-кнопки размеров добавляются в ask_for_width (bot_handlers.py).
"""

from __future__ import annotations

import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler

from .config import (
    AWAIT_BG_COLOR,
    AWAIT_TEXT_LINES,
    AWAIT_WIDTH,
    MAIN_MENU,
    MAX_DIMENSION,
    MIN_DIMENSION,
)
from .template_manager import get_template_manager

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Вспомогательные функции построения клавиатур
# ---------------------------------------------------------------------------

def build_sizes_keyboard() -> InlineKeyboardMarkup:
    """Инлайн-клавиатура типовых размеров + кнопка ручного ввода."""
    tm = get_template_manager()
    buttons = []
    row = []
    for i, size in enumerate(tm.get_sizes()):
        row.append(
            InlineKeyboardButton(
                size["label"],
                callback_data=f"tpl_size:{size['key']}",
            )
        )
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append(
        [InlineKeyboardButton("✏️ Ввести вручную", callback_data="tpl_size:manual")]
    )
    return InlineKeyboardMarkup(buttons)


def build_slogan_categories_keyboard() -> InlineKeyboardMarkup:
    """Инлайн-клавиатура категорий слоганов + отмена."""
    tm = get_template_manager()
    buttons = [
        [InlineKeyboardButton(cat, callback_data=f"tpl_scat:{cat}")]
        for cat in tm.get_slogan_categories()
    ]
    buttons.append(
        [InlineKeyboardButton("✖️ Отмена", callback_data="tpl_slogan_cancel")]
    )
    return InlineKeyboardMarkup(buttons)


def build_slogans_keyboard(category: str) -> InlineKeyboardMarkup:
    """Инлайн-клавиатура слоганов выбранной категории + назад."""
    tm = get_template_manager()
    slogans = tm.get_slogans_by_category(category)
    buttons = [
        [InlineKeyboardButton(slogan, callback_data=f"tpl_slogan:{i}")]
        for i, slogan in enumerate(slogans)
    ]
    buttons.append(
        [InlineKeyboardButton("↩️ Назад", callback_data="tpl_slogan_cancel")]
    )
    return InlineKeyboardMarkup(buttons)


def build_color_schemes_keyboard() -> InlineKeyboardMarkup:
    """Инлайн-клавиатура готовых цветовых схем + отмена."""
    tm = get_template_manager()
    buttons = [
        [
            InlineKeyboardButton(
                f"{scheme['preview']}",
                callback_data=f"tpl_color:{scheme['key']}",
            )
        ]
        for scheme in tm.get_color_schemes()
    ]
    buttons.append(
        [InlineKeyboardButton("✖️ Отмена", callback_data="tpl_color_cancel")]
    )
    return InlineKeyboardMarkup(buttons)


# ---------------------------------------------------------------------------
# Handlers: размеры
# ---------------------------------------------------------------------------

async def tpl_size_chosen(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Пользователь выбрал типовой размер или «Ввести вручную».
    Вызывается из состояния AWAIT_WIDTH.
    """
    query = update.callback_query
    await query.answer()

    key = query.data.split(":", 1)[1]

    if key == "manual":
        await query.edit_message_text(
            f"Введите ширину в мм (от {MIN_DIMENSION} до {MAX_DIMENSION}):"
        )
        return AWAIT_WIDTH

    tm = get_template_manager()
    size = tm.get_size_by_key(key)
    if not size:
        await query.edit_message_text("Размер не найден. Введите вручную:")
        return AWAIT_WIDTH

    config = context.user_data.setdefault("config", {})
    config["width"] = size["width_mm"]
    config["height"] = size["height_mm"]

    await query.edit_message_text(
        f"✅ Размер выбран: {size['label']}\n"
        f"Ширина: {size['width_mm']} мм, Высота: {size['height_mm']} мм"
    )

    # Возвращаемся в главное меню — display_menu вызовет вызывающая сторона
    from .bot_handlers import display_menu
    await display_menu(update.effective_message, context)
    return MAIN_MENU


# ---------------------------------------------------------------------------
# Handlers: слоганы
# ---------------------------------------------------------------------------

async def tpl_slogan_category(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Пользователь выбрал категорию слоганов.
    Вызывается из состояния AWAIT_TEXT_LINES.
    """
    query = update.callback_query
    await query.answer()

    category = query.data.split(":", 1)[1]
    context.user_data["tpl_slogan_category"] = category

    tm = get_template_manager()
    slogans = tm.get_slogans_by_category(category)
    if not slogans:
        await query.edit_message_text("Слоганы не найдены. Введите текст вручную:")
        return AWAIT_TEXT_LINES

    await query.edit_message_text(
        f"Категория: <b>{category}</b>\nВыберите слоган:",
        parse_mode="HTML",
        reply_markup=build_slogans_keyboard(category),
    )
    return AWAIT_TEXT_LINES


async def tpl_slogan_chosen(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Пользователь выбрал конкретный слоган.
    Вставляет его как очередную строку текста и продолжает воронку.
    """
    query = update.callback_query
    await query.answer()

    idx = int(query.data.split(":", 1)[1])
    category = context.user_data.get("tpl_slogan_category", "")

    tm = get_template_manager()
    slogans = tm.get_slogans_by_category(category)

    if not slogans or idx >= len(slogans):
        await query.edit_message_text("Слоган не найден. Введите текст вручную:")
        return AWAIT_TEXT_LINES

    slogan = slogans[idx]
    config = context.user_data.setdefault("config", {})
    config.setdefault("text_lines", []).append({"text": slogan, "scale": 1.0})

    # Чистим временный ключ
    context.user_data.pop("tpl_slogan_category", None)

    line_count = config.get("line_count", 0)
    current_count = len(config["text_lines"])

    if current_count < line_count:
        next_num = current_count + 1
        await query.edit_message_text(
            f"✅ Слоган добавлен: «{slogan}»\n\nВведите текст для строки {next_num}:"
        )
        return AWAIT_TEXT_LINES
    else:
        await query.edit_message_text(f"✅ Слоган добавлен: «{slogan}»\nВесь текст сохранён!")
        from .bot_handlers import display_menu
        await display_menu(update.effective_message, context)
        return MAIN_MENU


async def tpl_slogan_cancel(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Пользователь отменил выбор слогана — возврат к ручному вводу текста."""
    query = update.callback_query
    await query.answer()

    context.user_data.pop("tpl_slogan_category", None)

    config = context.user_data.get("config", {})
    next_num = len(config.get("text_lines", [])) + 1
    await query.edit_message_text(f"Введите текст для строки {next_num}:")
    return AWAIT_TEXT_LINES


# ---------------------------------------------------------------------------
# Handlers: цветовые схемы
# ---------------------------------------------------------------------------

async def tpl_color_chosen(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Пользователь выбрал готовую цветовую схему.
    Устанавливает bg_color и text_color в config.
    Вызывается из состояния AWAIT_BG_COLOR.
    """
    query = update.callback_query
    await query.answer()

    key = query.data.split(":", 1)[1]
    tm = get_template_manager()
    scheme = tm.get_color_scheme_by_key(key)

    if not scheme:
        await query.edit_message_text("Схема не найдена. Выберите цвет вручную:")
        return AWAIT_BG_COLOR

    config = context.user_data.setdefault("config", {})
    config["bg_color"] = scheme["bg"]
    config["text_color"] = scheme["text"]

    await query.edit_message_text(
        f"✅ Схема выбрана: {scheme['label']}\n"
        f"Фон: {scheme['bg']}, Текст: {scheme['text']}"
    )

    from .bot_handlers import display_menu
    await display_menu(update.effective_message, context)
    return MAIN_MENU


async def tpl_color_cancel(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Пользователь отменил выбор схемы — возврат к ручному выбору цвета."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Выберите цвет из списка ниже:")
    return AWAIT_BG_COLOR
