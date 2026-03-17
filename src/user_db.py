"""
user_db.py
~~~~~~~~~~
SQLite-хранилище: пользователи и платежи.
WAL-режим для concurrent-доступа из async-контекста.

Таблицы:
  users    — профиль пользователя + реферальная цепочка
  payments — история оплат (Telegram Stars)
"""

import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

DB_PATH = "/app/data/banner_bot.db"


# ---------------------------------------------------------------------------
# Инициализация
# ---------------------------------------------------------------------------

def init_db(db_path: str = DB_PATH) -> None:
    """Создаёт таблицы при первом запуске. Безопасно вызывать повторно."""
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

            CREATE INDEX IF NOT EXISTS idx_payments_tg_id ON payments(tg_id);
        """)
    logger.info("БД инициализирована: %s", db_path)


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
            # Проверяем, существует ли referrer — нельзя вставить несуществующий FK
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
        row = conn.execute("SELECT COALESCE(SUM(stars), 0) FROM payments").fetchone()
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
