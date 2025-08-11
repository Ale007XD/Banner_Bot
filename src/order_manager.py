import json
import os
from datetime import datetime

COUNTER_FILE_PATH = "order_counter.json"

def _read_counter():
    """Читает данные счетчика из файла."""
    try:
        with open(COUNTER_FILE_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"total_ever": 0, "daily": {}}

def _write_counter(data):
    """Записывает данные счетчика в файл с защитой от гонок."""
    with open(COUNTER_FILE_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
        f.flush()  # Принудительная запись в буфер ОС
        os.fsync(f.fileno())  # Синхронизация с диском для атомарности

def get_next_order_number() -> str:
    """Генерирует следующий номер заказа и обновляет статистику."""
    today_str = datetime.now().strftime("%Y-%m-%d")
    today_formatted = datetime.now().strftime("%d%m")
    
    data = _read_counter()
    
    # Обновляем счетчик за сегодня
    daily_count = data.get("daily", {}).get(today_str, 0) + 1
    if "daily" not in data:
        data["daily"] = {}
    data["daily"][today_str] = daily_count
    
    # Обновляем общий счетчик
    data["total_ever"] = data.get("total_ever", 0) + 1
    
    _write_counter(data)
    
    order_number = f"ДА-{today_formatted}-{daily_count:03d}"
    return order_number

def get_stats() -> str:
    """Возвращает строку со статистикой."""
    today_str = datetime.now().strftime("%Y-%m-%d")
    data = _read_counter()
    
    orders_today = data.get("daily", {}).get(today_str, 0)
    orders_total = data.get("total_ever", 0)
    
    return f"📊 **Статистика заказов**\n\n- За сегодня: `{orders_today}`\n- Всего за все время: `{orders_total}`"
