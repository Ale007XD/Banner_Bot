import json
from datetime import datetime

# Файл будет создан в корневой папке проекта на сервере
COUNTER_FILE_PATH = "order_counter.json"

def get_next_order_number() -> str:
    """
    Генерирует следующий номер заказа в формате ДА-(ддмм)-xxx.
    Счетчик сбрасывается каждый день. Состояние хранится в JSON-файле.
    """
    today_str = datetime.now().strftime("%Y-%m-%d")
    today_formatted = datetime.now().strftime("%d%m")
    
    current_index = 1

    try:
        with open(COUNTER_FILE_PATH, 'r') as f:
            data = json.load(f)
            last_date_str = data.get("date")
            last_index = data.get("last_order_index")

            if last_date_str == today_str:
                # Если дата та же, увеличиваем счетчик
                current_index = last_index + 1
            # Если дата другая, счетчик сбрасывается (остается 1)

    except (FileNotFoundError, json.JSONDecodeError):
        # Файл не найден или пуст/некорректен, начинаем с 1
        pass

    # Сохраняем новое состояние обратно в файл
    with open(COUNTER_FILE_PATH, 'w') as f:
        json.dump({
            "date": today_str,
            "last_order_index": current_index
        }, f)

    # Форматируем финальный номер заказа
    # :03d - означает, что число будет дополнено нулями до 3 знаков (1 -> 001)
    order_number = f"ДА-{today_formatted}-{current_index:03d}"
    
    return order_number
