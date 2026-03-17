"""
payment_handlers.py
~~~~~~~~~~~~~~~~~~~
Обработчики платёжного флоу Telegram Stars.

Флоу:
  generate_pdf_callback (bot_handlers.py)
      → send_pdf_invoice()          — отправляет инвойс
      → pre_checkout_handler()      — подтверждает PreCheckoutQuery
      → successful_payment_handler() — генерирует PDF и отправляет файл

Payload инвойса: "pdf:{tg_id}:{order_number}"
Позволяет однозначно восстановить контекст заказа в successful_payment_handler.
"""

import logging
from typing import Optional

from telegram import Update, LabeledPrice
from telegram.ext import ContextTypes

from .config import STARS_PRICE
from .user_db import record_payment, upsert_user

logger = logging.getLogger(__name__)

# Ключ в context.user_data, куда bot_handlers складывает данные заказа
# перед вызовом send_pdf_invoice.
# Структура: {"order_number": str, "banner_params": dict}
PENDING_ORDER_KEY = "pending_pdf_order"


# ---------------------------------------------------------------------------
# Отправка инвойса
# ---------------------------------------------------------------------------

async def send_pdf_invoice(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    order_number: str,
) -> None:
    """
    Вызывается из generate_pdf_callback вместо прямой генерации PDF.
    Сохраняет order_number в user_data и отправляет Stars-инвойс.
    """
    user = update.effective_user
    tg_id = user.id

    # Гарантируем наличие пользователя в БД
    upsert_user(
        tg_id=tg_id,
        username=user.username,
        first_name=user.first_name,
    )

    # Сохраняем order_number для successful_payment_handler
    context.user_data[PENDING_ORDER_KEY] = {"order_number": order_number}

    payload = f"pdf:{tg_id}:{order_number}"

    await context.bot.send_invoice(
        chat_id=tg_id,
        title="PDF для типографии",
        description=(
            f"Печатный баннер #{order_number}. "
            "CMYK, PDF/A-1, профиль ISOcoated_v2_300_eci."
        ),
        payload=payload,
        currency="XTR",           # Telegram Stars
        prices=[
            LabeledPrice(label="PDF-файл", amount=STARS_PRICE)
        ],
        # photo_url можно добавить позже (превью баннера)
    )
    logger.info("Инвойс отправлен: tg_id=%s order=%s stars=%s", tg_id, order_number, STARS_PRICE)


# ---------------------------------------------------------------------------
# PreCheckoutQuery — обязательное подтверждение в течение 10 секунд
# ---------------------------------------------------------------------------

async def pre_checkout_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Всегда подтверждаем — валидация заказа происходит в successful_payment_handler."""
    query = update.pre_checkout_query
    await query.answer(ok=True)
    logger.info("PreCheckoutQuery подтверждён: id=%s", query.id)


# ---------------------------------------------------------------------------
# SuccessfulPayment — генерация и отправка PDF
# ---------------------------------------------------------------------------

async def successful_payment_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """
    Срабатывает после подтверждения оплаты Telegram.
    Восстанавливает параметры заказа из user_data, генерирует PDF, отправляет.
    """
    from .banner_generator import create_print_pdf  # локальный импорт — избегаем цикла
    from .order_manager import get_banner_params_from_context  # аналогично

    payment = update.message.successful_payment
    user = update.effective_user
    tg_id = user.id

    # Парсим payload: "pdf:{tg_id}:{order_number}"
    parts = payment.invoice_payload.split(":")
    if len(parts) != 3 or parts[0] != "pdf":
        logger.error("Неожиданный payload: %s", payment.invoice_payload)
        await update.message.reply_text(
            "⚠️ Платёж получен, но заказ не найден. Напишите в поддержку."
        )
        return

    order_number = parts[2]

    # Записываем платёж в БД
    record_payment(
        tg_id=tg_id,
        stars=payment.total_amount,
        order_number=order_number,
        payload=payment.invoice_payload,
    )
    logger.info("Платёж записан: tg_id=%s order=%s stars=%s", tg_id, order_number, payment.total_amount)

    await update.message.reply_text("✅ Оплата получена! Генерирую PDF…")

    # Получаем параметры баннера из user_data (их кладёт bot_handlers.py)
    try:
        banner_params = get_banner_params_from_context(context)
        pdf_bytes = create_print_pdf(**banner_params)
    except Exception as exc:
        logger.exception("Ошибка генерации PDF: %s", exc)
        await update.message.reply_text(
            "⚠️ Ошибка генерации PDF. Попробуйте ещё раз или обратитесь в поддержку."
        )
        return

    filename = f"banner_{order_number}.pdf"
    await update.message.reply_document(
        document=pdf_bytes,
        filename=filename,
        caption=(
            f"🖨 Ваш баннер #{order_number} готов к печати.\n"
            "PDF/A-1, CMYK, ISOcoated_v2_300_eci."
        ),
    )

    # Чистим pending — заказ закрыт
    context.user_data.pop(PENDING_ORDER_KEY, None)
    logger.info("PDF отправлен: tg_id=%s order=%s", tg_id, order_number)
