# Используем легковесный базовый образ Python
FROM python:3.10-slim

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

# Копируем файл с зависимостями
COPY requirements.txt .

# Устанавливаем зависимости, не кешируя их
RUN pip install --no-cache-dir -r requirements.txt

# Копируем папку со шрифтами
COPY fonts/ ./fonts/

# Копируем исходный код приложения
COPY src/ ./src/

# Команда для запуска бота при старте контейнера
CMD ["python", "src/main.py"]
