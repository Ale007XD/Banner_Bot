"""
user_db.py
~~~~~~~~~~
SQLite-хранилище: пользователи, платежи, лог доставки, воронка.
WAL-режим для concurrent-доступа из async-контекста.

Таблицы:
  users        — профиль пользователя + реферальная цепочка
  payments     — история оплат (Telegram Stars)
  delivery_log — доказательная база доставки PDF (152-ФЗ: исполнение договора)
  funnel_events — события воронки для расчёта конверсии

152-ФЗ / минимизация рисков:
  - tg_id хранится на основании исполнения договора (оферта, ст. 6 п. 5 152-ФЗ)
  - file_hash (SHA-256) и tg_message_id не являются персональными данными
  - delivery_log автоматически очищается через TTL_DAYS (по умолчанию 14 суток)
  - очистка запускается при каждом вызове init_db() и purge_expired_deliveries()
"""

import hashlib
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

DB_PATH = "/app/data/banner_bot.db"

# Срок хранения записей delivery_log в сутках.
# Достаточен для разбора апелляций по Telegram Stars.
# Прописать в оферте: «Логи доставки хранятся 14 суток».
DELIVERY_TTL_DAYS = 14

# Константы событий воронки — использовать везде вместо строк напрямую
FUNNEL_PREVIEW_GENERATED = "preview_generated"
FUNNEL_INVOICE_SENT      = "invoice_sent"
FUNNEL_PAYMENT_COMPLETED = "payment_completed"


# ---------------------------------------------------------------------------
# Инициализация
# ---------------------------------------------------------------------------

def init_db(db_path: str = DB_PATH) -> None:
    """
    Создаёт таблицы при первом запуске. Безопасно вызывать повторно.
    Запускает миграции и TTL-очистку delivery_log.
    """
    with _connect(db_path) as conn:
        conn.executescript("""
            PRAGMA journal_mode=WAL;
            PRAGMA foreign_keys=ON;

            CREATE TABLE IF NOT EXISTS users (
                tg_id       INTEGER PRIMARY KEY,
                username    TEXT,
                first_name  TEXT,
                created_at  TEXT NOT NULL,
                referrer_id INTEGER REFERENCES users(tg_id)
            );

            CREATE TABLE IF NOT EXISTS payments (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id        INTEGER NOT NULL REFERENCES users(tg_id),
                order_number TEXT,
                stars        INTEGER NOT NULL,
                payload      TEXT,
                created_at   TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_payments_tg_id
                ON payments(tg_id);

            -- Лог доставки PDF.
            -- Основание хранения tg_id: исполнение договора (оферта).
            -- Остальные поля — технические идентификаторы, не ПД.
            CREATE TABLE IF NOT EXISTS delivery_log (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                order_number   TEXT    NOT NULL,
                tg_id          INTEGER NOT NULL REFERENCES users(tg_id),
                stars_tx_id    TEXT,                -- Telegram payment_charge_id
                file_hash      TEXT    NOT NULL,    -- SHA-256 от print_ready.pdf
                tg_message_id  INTEGER,             -- message_id ответа бота
                delivered_at   TEXT    NOT NULL,    -- UTC ISO-8601
                ttl_delete_at  TEXT    NOT NULL,    -- delivered_at + TTL_DAYS
                status         TEXT    NOT NULL DEFAULT 'delivered'
                                        CHECK(status IN ('delivered', 'failed', 'pending'))
            );

            CREATE INDEX IF NOT EXISTS idx_delivery_order
                ON delivery_log(order_number);

            CREATE INDEX IF NOT EXISTS idx_delivery_ttl
                ON delivery_log(ttl_delete_at);

            -- Воронка конверсии.
            -- tg_id хранится на том же основании что и в остальных таблицах.
            -- event: preview_generated | invoice_sent | payment_completed
            CREATE TABLE IF NOT EXISTS funnel_events (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id        INTEGER NOT NULL REFERENCES users(tg_id),
                event        TEXT    NOT NULL
                                     CHECK(event IN (
                                         'preview_generated',
                                         'invoice_sent',
                                         'payment_completed'
                                     )),
                order_number TEXT,       -- NULL для preview_generated
                created_at   TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_funnel_event
                ON funnel_events(event);

            CREATE INDEX IF NOT EXISTS idx_funnel_tg_id
                ON funnel_events(tg_id);
        """)

    _run_migrations(db_path)
    purge_expired_deliveries(db_path)
    logger.info("БД инициализирована: %s", db_path)


def _run_migrations(db_path: str = DB_PATH) -> None:
    """Идемпотентные проверки схемы для существующих БД."""
    with _connect(db_path) as conn:
        tables = {
            row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        for table in ("delivery_log", "funnel_events"):
            if table not in tables:
                logger.info(
                    "Миграция: таблица %s будет создана при следующем init_db",
                    table,
                )


# ---------------------------------------------------------------------------
# Внутренние утилиты
# ---------------------------------------------------------------------------

@contextmanager
def _connect(db_path: str = DB_PATH):
    """Контекстный менеджер соединения с row_factory."""
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds")


def _ttl_deadline() -> str:
    return (datetime.utcnow() + timedelta(days=DELIVERY_TTL_DAYS)).isoformat(
        timespec="seconds"
    )


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

def upsert_user(
    tg_id: int,
    username: Optional[str],
    first_name: Optional[str],
    referrer_id: Optional[int] = None,
    db_path: str = DB_PATH,
) -> None:
    """
    Регистрирует нового пользователя или обновляет username/first_name.
    referrer_id учитывается только при первой вставке.
    """
    with _connect(db_path) as conn:
        existing = conn.execute(
            "SELECT tg_id FROM users WHERE tg_id = ?", (tg_id,)
        ).fetchone()

        if existing:
            conn.execute(
                "UPDATE users SET username = ?, first_name = ? WHERE tg_id = ?",
                (username, first_name, tg_id),
            )
        else:
            if referrer_id is not None:
                ref_exists = conn.execute(
                    "SELECT tg_id FROM users WHERE tg_id = ?", (referrer_id,)
                ).fetchone()
                if not ref_exists:
                    referrer_id = None

            conn.execute(
                """
                INSERT INTO users (tg_id, username, first_name, created_at, referrer_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                (tg_id, username, first_name, _now(), referrer_id),
            )


def get_user(tg_id: int, db_path: str = DB_PATH) -> Optional[sqlite3.Row]:
    with _connect(db_path) as conn:
        return conn.execute(
            "SELECT * FROM users WHERE tg_id = ?", (tg_id,)
        ).fetchone()


def get_total_users(db_path: str = DB_PATH) -> int:
    with _connect(db_path) as conn:
        row = conn.execute("SELECT COUNT(*) FROM users").fetchone()
        return row[0]


# ---------------------------------------------------------------------------
# Payments
# ---------------------------------------------------------------------------

def record_payment(
    tg_id: int,
    stars: int,
    order_number: Optional[str] = None,
    payload: Optional[str] = None,
    db_path: str = DB_PATH,
) -> int:
    """Записывает успешный платёж. Возвращает id новой записи."""
    with _connect(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO payments (tg_id, order_number, stars, payload, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (tg_id, order_number, stars, payload, _now()),
        )
        return cursor.lastrowid


def get_payments_by_user(
    tg_id: int, db_path: str = DB_PATH
) -> list[sqlite3.Row]:
    with _connect(db_path) as conn:
        return conn.execute(
            "SELECT * FROM payments WHERE tg_id = ? ORDER BY created_at DESC",
            (tg_id,),
        ).fetchall()


def get_total_revenue(db_path: str = DB_PATH) -> int:
    """Суммарный доход в Stars."""
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT COALESCE(SUM(stars), 0) FROM payments"
        ).fetchone()
        return row[0]


def get_total_orders(db_path: str = DB_PATH) -> int:
    """Количество оплаченных заказов."""
    with _connect(db_path) as conn:
        row = conn.execute("SELECT COUNT(*) FROM payments").fetchone()
        return row[0]


def get_recent_payments(
    limit: int = 10, db_path: str = DB_PATH
) -> list[sqlite3.Row]:
    with _connect(db_path) as conn:
        return conn.execute(
            """
            SELECT p.*, u.username, u.first_name
            FROM payments p
            LEFT JOIN users u ON p.tg_id = u.tg_id
            ORDER BY p.created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()


# ---------------------------------------------------------------------------
# Referrals
# ---------------------------------------------------------------------------

def get_referral_count(tg_id: int, db_path: str = DB_PATH) -> int:
    """Сколько пользователей пришло по реферальной ссылке tg_id."""
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM users WHERE referrer_id = ?", (tg_id,)
        ).fetchone()
        return row[0]


# ---------------------------------------------------------------------------
# Delivery log
# ---------------------------------------------------------------------------

def compute_file_hash(data: bytes) -> str:
    """SHA-256 от содержимого файла. Принимает bytes."""
    return hashlib.sha256(data).hexdigest()


def record_delivery(
    order_number: str,
    tg_id: int,
    file_hash: str,
    stars_tx_id: Optional[str] = None,
    tg_message_id: Optional[int] = None,
    status: str = "delivered",
    db_path: str = DB_PATH,
) -> int:
    """
    Записывает факт доставки PDF пользователю.

    Аргументы:
        order_number   — номер заказа (не ПД)
        tg_id          — Telegram ID (ПД; основание: исполнение договора)
        file_hash      — SHA-256 от print_ready.pdf (не ПД)
        stars_tx_id    — telegram_payment_charge_id из SuccessfulPayment
        tg_message_id  — message_id сообщения с PDF
        status         — 'delivered' | 'failed' | 'pending'

    Возвращает id новой записи.
    """
    with _connect(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO delivery_log
                (order_number, tg_id, stars_tx_id, file_hash,
                 tg_message_id, delivered_at, ttl_delete_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                order_number,
                tg_id,
                stars_tx_id,
                file_hash,
                tg_message_id,
                _now(),
                _ttl_deadline(),
                status,
            ),
        )
        logger.info(
            "[DELIVERY] order=%s tg_id=%s status=%s hash=%.16s…",
            order_number, tg_id, status, file_hash,
        )
        return cursor.lastrowid


def get_delivery(
    order_number: str, db_path: str = DB_PATH
) -> Optional[sqlite3.Row]:
    """Возвращает запись лога по номеру заказа (для апелляций)."""
    with _connect(db_path) as conn:
        return conn.execute(
            "SELECT * FROM delivery_log WHERE order_number = ?",
            (order_number,),
        ).fetchone()


def purge_expired_deliveries(db_path: str = DB_PATH) -> int:
    """
    Удаляет записи delivery_log с истёкшим TTL.
    Вызывается автоматически из init_db().
    Возвращает количество удалённых строк.
    """
    now = _now()
    with _connect(db_path) as conn:
        cursor = conn.execute(
            "DELETE FROM delivery_log WHERE ttl_delete_at <= ?", (now,)
        )
        deleted = cursor.rowcount

    if deleted:
        logger.info("[TTL] Удалено записей delivery_log: %d", deleted)
    return deleted


# ---------------------------------------------------------------------------
# Funnel events
# ---------------------------------------------------------------------------

def record_funnel_event(
    tg_id: int,
    event: str,
    order_number: Optional[str] = None,
    db_path: str = DB_PATH,
) -> None:
    """
    Фиксирует событие воронки.

    Использовать константы:
        FUNNEL_PREVIEW_GENERATED  — превью показано пользователю
        FUNNEL_INVOICE_SENT       — инвойс выставлен (нажата кнопка PDF)
        FUNNEL_PAYMENT_COMPLETED  — оплата подтверждена Telegram
    """
    with _connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO funnel_events (tg_id, event, order_number, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (tg_id, event, order_number, _now()),
        )


def get_funnel_stats(db_path: str = DB_PATH) -> dict:
    """
    Возвращает словарь с показателями воронки за всё время:
        previews  — сколько раз показано превью
        invoices  — сколько раз выставлен инвойс
        payments  — сколько оплат завершено
        conv_pct  — конверсия превью → оплата (%)
    """
    with _connect(db_path) as conn:
        row = conn.execute("""
            SELECT
                COUNT(CASE WHEN event = 'preview_generated' THEN 1 END) AS previews,
                COUNT(CASE WHEN event = 'invoice_sent'      THEN 1 END) AS invoices,
                COUNT(CASE WHEN event = 'payment_completed' THEN 1 END) AS payments,
                ROUND(
                    100.0
                    * COUNT(CASE WHEN event = 'payment_completed' THEN 1 END)
                    / NULLIF(
                        COUNT(CASE WHEN event = 'preview_generated' THEN 1 END), 0
                    ),
                    1
                ) AS conv_pct
            FROM funnel_events
        """).fetchone()

    return {
        "previews": row["previews"],
        "invoices": row["invoices"],
        "payments": row["payments"],
        "conv_pct": row["conv_pct"] or 0.0,
    }
