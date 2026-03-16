FROM python:3.10-slim

WORKDIR /app

# Устанавливаем системные зависимости:
# ghostscript — конвертация PDF в PDF/X с CMYK-профилем и шрифтами в кривых
# curl — для скачивания ICC-профиля
# libgl1, libglib2.0-0 — зависимости Pillow
RUN apt-get update && apt-get install -y \
    ghostscript \
    curl \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Скачиваем стандартный ICC-профиль ISOcoated_v2_300 (офсетная печать, Europe)
# Это самый распространённый профиль, принимаемый типографиями
RUN mkdir -p /profiles && \
    curl -L -o /profiles/ISOcoated_v2_300_eci.icc \
    "https://www.color.org/registry/ISOcoated_v2_300_eci.icc" || \
    echo "WARNING: ICC profile download failed, will use fallback"

# Копируем зависимости и устанавливаем их отдельным слоем (кэширование)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код и шрифты
COPY src/ ./src/
COPY fonts/ ./fonts/

# Директория для хранения заказов (монтируется как volume в docker-compose)
RUN mkdir -p /app/orders

CMD ["python", "-m", "src.main"]
