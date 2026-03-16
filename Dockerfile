FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    ghostscript \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Создаем папку для профилей и копируем ICC-профиль из вашего репозитория
RUN mkdir -p /profiles /app/orders /app/data
COPY assets/profiles/ISOcoated_v2_300_eci.icc /profiles/ISOcoated_v2_300_eci.icc

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY fonts/ ./fonts/

CMD ["python", "-m", "src.main"]
