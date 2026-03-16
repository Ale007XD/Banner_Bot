"""
order_manager.py
~~~~~~~~~~~~~~~~
Счётчик заказов с персистентностью (JSON-файл) и защитой от race condition.

Формат номера заказа: ДА-ДДММ-NNN
  ДА   — префикс ("Дизайн/Агентство" или любой другой смысл)
  ДДММ — день и месяц
  NNN  — порядковый номер за день (с ведущими нулями)
"""

import json
import logging
import threading
from datetime import datetime

from .config import COUNTER_FILE_PATH

logger = logging.getLogger(__name__)

# Глобальный Lock: гарантирует атомарность read-modify-write
# при конкурентных вызовах из разных потоков Telegram-обработчиков
_lock = threading.Lock()


def _read_counter() -> dict:
    try:
        with open(COUNTER_FILE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"total_ever": 0, "daily": {}}


def _write_counter(data: dict) -> None:
    with open(COUNTER_FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def get_next_order_number() -> str:
    """
    Генерирует следующий уникальный номер заказа и обновляет статистику.
    Потокобезопасен благодаря threading.Lock.
    """
    with _lock:
        today_str = datetime.now().strftime("%Y-%m-%d")
        today_fmt = datetime.now().strftime("%d%m")

        data = _read_counter()
        daily = data.setdefault("daily", {})

        daily_count = daily.get(today_str, 0) + 1
        daily[today_str] = daily_count
        data["total_ever"] = data.get("total_ever", 0) + 1

        _write_counter(data)

    order_number = f"ДА-{today_fmt}-{daily_count:03d}"
    logger.info("Создан заказ %s (всего: %d)", order_number, data["total_ever"])
    return order_number


def get_stats() -> str:
    """Возвращает отформатированную строку статистики для команды /stats."""
    today_str = datetime.now().strftime("%Y-%m-%d")

    with _lock:
        data = _read_counter()

    orders_today = data.get("daily", {}).get(today_str, 0)
    orders_total = data.get("total_ever", 0)

    # Топ-5 дней по количеству заказов
    daily = data.get("daily", {})
    top_days = sorted(daily.items(), key=lambda x: x[1], reverse=True)[:5]
    top_lines = "\n".join(
        f"  `{day}`: {count} заказ(ов)" for day, count in top_days
    )

    return (
        f"📊 *Статистика заказов*\n\n"
        f"За сегодня: `{orders_today}`\n"
        f"Всего за всё время: `{orders_total}`\n\n"
        f"*Топ\\-5 дней:*\n{top_lines}"
    )
    
