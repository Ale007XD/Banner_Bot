FROM python:3.10-slim

WORKDIR /app

# Устанавливаем системные зависимости
# libgl1, libglib2.0-0 нужны для Pillow
RUN apt-get update && apt-get install -y \
    ghostscript \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Создаем необходимые директории
RUN mkdir -p /profiles /app/orders /app/data

# Копируем ICC-профиль из репозитория (скачайте его заранее в assets/profiles/)
COPY assets/profiles/ISOcoated_v2_300_eci.icc /profiles/ISOcoated_v2_300_eci.icc

# Установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код и ресурсы
COPY src/ ./src/
COPY fonts/ ./fonts/

# Запуск через модуль
CMD ["python", "-m", "src.main"]
