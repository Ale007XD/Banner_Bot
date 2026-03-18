"""
payment_handlers.py
~~~~~~~~~~~~~~~~~~~
Обработчики платёжного флоу Telegram Stars.

Флоу:
  generate_pdf_callback (bot_handlers.py)
      → send_pdf_invoice()           — отправляет инвойс
      → pre_checkout_handler()       — подтверждает PreCheckoutQuery
      → successful_payment_handler() — генерирует PDF и отправляет файл

Payload инвойса: "pdf:{tg_id}:{order_number}"
Позволяет однозначно восстановить контекст заказа в successful_payment_handler.
"""

import logging
import os
from datetime import datetime, timezone

from telegram import Update, LabeledPrice
from telegram.ext import ContextTypes

from .config import STARS_PRICE
from .user_db import (
    FUNNEL_PAYMENT_COMPLETED,
    compute_file_hash,
    record_delivery,
    record_funnel_event,
    record_payment,
    upsert_user,
)
from .config import ORDERS_DIR, POSTPRINT_NONE, TELEGRAM_CHANNEL_ID

logger = logging.getLogger(__name__)

# Ключ в context.user_data, куда bot_handlers складывает данные заказа
# перед вызовом send_pdf_invoice.
# Структура: {"order_number": str, "postprint_code": str, "config": dict}
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
    Отправляет Stars-инвойс.
    """
    user = update.effective_user
    tg_id = user.id

    upsert_user(
        tg_id=tg_id,
        username=user.username,
        first_name=user.first_name,
    )

    payload = f"pdf:{tg_id}:{order_number}"

    await context.bot.send_invoice(
        chat_id=tg_id,
        title="PDF для типографии",
        description=(
            f"Печатный баннер #{order_number}. "
            "CMYK, PDF/A-1, профиль ISOcoated_v2_300_eci."
        ),
        payload=payload,
        currency="XTR",
        prices=[LabeledPrice(label="PDF-файл", amount=STARS_PRICE)],
        provider_token="",
    )
    logger.info(
        "Инвойс отправлен: tg_id=%s order=%s stars=%s",
        tg_id, order_number, STARS_PRICE,
    )


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
    Читает config из pending_pdf_order, генерирует PDF,
    отправляет пользователю и уведомляет служебный канал.
    После отправки вызывает display_menu для продолжения работы.
    """
    from .banner_generator import create_final_pdf
    from .bot_handlers import display_menu

    payment = update.message.successful_payment
    user = update.effective_user
    tg_id = user.id
    stars_tx_id = payment.telegram_payment_charge_id

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

    # Воронка: оплата завершена
    record_funnel_event(
        tg_id=tg_id,
        event=FUNNEL_PAYMENT_COMPLETED,
        order_number=order_number,
    )

    logger.info(
        "Платёж записан: tg_id=%s order=%s stars=%s tx=%s",
        tg_id, order_number, payment.total_amount, stars_tx_id,
    )

    await update.message.reply_text("✅ Оплата получена! Генерирую PDF…")

    # Восстанавливаем контекст заказа
    pending = context.user_data.get(PENDING_ORDER_KEY, {})
    config = pending.get("config")
    postprint_code = pending.get("postprint_code", "XX")

    if not config:
        logger.error("config не найден в pending_pdf_order: tg_id=%s", tg_id)
        record_delivery(
            order_number=order_number,
            tg_id=tg_id,
            file_hash="0" * 64,
            stars_tx_id=stars_tx_id,
            tg_message_id=None,
            status="failed",
        )
        await update.message.reply_text(
            "⚠️ Данные заказа утеряны (бот перезапускался?). "
            "Сформируйте баннер заново — оплата уже засчитана."
        )
        return

    # Генерация PDF
    try:
        pdf_buf = create_final_pdf(config)
    except Exception as exc:
        logger.exception("Ошибка генерации PDF: tg_id=%s order=%s", tg_id, order_number)
        record_delivery(
            order_number=order_number,
            tg_id=tg_id,
            file_hash="0" * 64,
            stars_tx_id=stars_tx_id,
            tg_message_id=None,
            status="failed",
        )
        await update.message.reply_text(
            f"⚠️ Ошибка генерации PDF: {exc}\n"
            "Обратитесь в поддержку — оплата засчитана."
        )
        return

    pdf_bytes = pdf_buf.getvalue()
    file_hash = compute_file_hash(pdf_bytes)
    filename = f"order_{order_number}_{postprint_code}.pdf"

    # Сохраняем на диск
    os.makedirs(ORDERS_DIR, exist_ok=True)
    file_path = os.path.join(ORDERS_DIR, filename)
    with open(file_path, "wb") as f:
        f.write(pdf_bytes)
    context.bot_data["last_order_path"] = file_path

    # Отправляем пользователю
    pdf_buf.seek(0)
    sent_message = await update.message.reply_document(
        document=pdf_buf,
        filename=filename,
        caption=(
            f"🖨 Ваш баннер #{order_number} готов к печати.\n"
            "PDF/A-1, CMYK, ISOcoated_v2_300_eci."
        ),
    )

    # Лог доставки (152-ФЗ)
    record_delivery(
        order_number=order_number,
        tg_id=tg_id,
        file_hash=file_hash,
        stars_tx_id=stars_tx_id,
        tg_message_id=sent_message.message_id,
        status="delivered",
    )

    # Служебное уведомление в канал — без ПД, только технические данные
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    channel_text = (
        f"🖨 Заказ №{order_number}\n"
        f"⭐ {payment.total_amount} Stars  |  tx: {stars_tx_id}\n"
        f"📐 {config['width']}×{config['height']} мм  |  Постпечать: {config['postprint']}\n"
        f"🎨 Фон: {config['bg_color']}  |  Текст: {config['text_color']}  |  Шрифт: {config['font']}\n"
        f"🔒 SHA-256: {file_hash[:16]}…\n"
        f"📨 msg\\_id: {sent_message.message_id}  |  {now_utc}"
    )
    await context.bot.send_message(
        chat_id=TELEGRAM_CHANNEL_ID,
        text=channel_text,
        parse_mode="Markdown",
    )

    # Чистим pending — заказ закрыт
    context.user_data.pop(PENDING_ORDER_KEY, None)
    context.user_data["config"] = {"postprint": POSTPRINT_NONE}
    logger.info(
        "PDF отправлен: tg_id=%s order=%s hash=%.16s… msg_id=%s",
        tg_id, order_number, file_hash, sent_message.message_id,
    )

    # Предлагаем создать новый баннер
    await display_menu(update.message, context)
