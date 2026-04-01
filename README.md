# Banner Bot 

Telegram-бот для генерации печатных баннеров. Принимает параметры через интерактивный диалог, формирует JPEG-превью с вотермаркой и PDF-файл, готовый для передачи в типографию. Оплата через Telegram Stars.

## 📋 Возможности

- Быстрый старт через шаблоны: типовые размеры, слоганы-триггеры, готовые цветовые схемы
- Настройка размеров баннера вручную (ширина и высота в мм, от 500 до 3000)
- Выбор цвета фона и текста из палитры
- Выбор шрифта с визуальным превью
- Ввод до 4 строк текста с индивидуальным масштабированием каждой строки
- Редактирование текста после ввода
- Санитизация пользовательского ввода (whitelist + SanitizeFlag)
- Выбор постпечатной обработки (люверсы)
- JPEG-превью с вотермаркой перед финальной генерацией
- PDF для типографии: **CMYK, ICC-профиль ISOcoated_v2\_300, шрифты в кривых, PDF/A-1b**
- Оплата PDF через **Telegram Stars** (инвойс → PreCheckout → доставка)
- Журнал доставки (`delivery_log`) с TTL 14 суток — доказательная база для апелляций Stars
- Воронка событий: `preview_generated` → `invoice_sent` → `payment_completed`
- Уведомление в служебный канал после оплаты (без ПД, без PDF)
- Нумерация заказов в формате `ДА-ДДММ-NNN`
- Сохранение состояния диалога между перезапусками (PicklePersistence)

## 🛠️ Технологии

| Компонент | Назначение |
|---|---|
| Python 3.10 | Основной язык |
| [python-telegram-bot 21](https://github.com/python-telegram-bot/python-telegram-bot) | Telegram Bot API, FSM (ConversationHandler) |
| [Pillow](https://python-pillow.org/) | Генерация JPEG-превью |
| [ReportLab](https://www.reportlab.com/) | Генерация промежуточного PDF |
| [Ghostscript 10.05.1](https://www.ghostscript.com/) | Постобработка: PDF/A-1b, CMYK+ICC, шрифты в кривых |
| SQLite (WAL) | Хранение пользователей, платежей, delivery_log, funnel_events |
| [python-dotenv](https://pypi.org/project/python-dotenv/) | Переменные окружения |
| Docker + Docker Compose | Контейнеризация и деплой |
| GitHub Actions | CI/CD: SCP → SSH → Docker |

## 📁 Структура проекта

```
Banner_Bot/
├── .github/
│   └── workflows/
│       ├── deploy.yaml          # CI/CD: деплой на VPS
│       └── project-snapshot.yml # Снапшот репозитория для LLM
├── assets/
│   └── profiles/
│       └── ISOcoated_v2_300_eci.icc  # ICC-профиль для типографии
├── fonts/
│   ├── FiraSans-Regular.ttf
│   ├── GolosText-Regular.ttf
│   ├── IgraSans-Regular.ttf
│   ├── TenorSans-Regular.ttf
│   └── README.md
├── src/
│   ├── __init__.py
│   ├── banner_generator.py   # JPEG-превью + двухшаговая генерация PDF
│   ├── bot_handlers.py       # FSM-обработчики диалога
│   ├── config.py             # Все константы: цвета, шрифты, состояния FSM
│   ├── main.py               # Точка входа, PicklePersistence, регистрация хендлеров
│   ├── order_manager.py      # Счётчик заказов (thread-safe)
│   ├── payment_handlers.py   # PreCheckout + successful_payment_handler
│   ├── template_handlers.py  # Обработчики коллбэков шаблонов
│   ├── template_manager.py   # Синглтон: get_template_manager(), методы get_sizes() и др.
│   ├── text_sanitizer.py     # Санитизация ввода: whitelist SAFE_CHARS_RE, SanitizeFlag
│   └── user_db.py            # SQLite: users, payments, delivery_log, funnel_events
├── templates.json            # Шаблоны: размеры, слоганы, цветовые схемы
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

## 🚀 Запуск

### Вариант 1: Локальный

1. Клонируйте репозиторий и перейдите в папку:
   ```bash
   git clone https://github.com/Ale007XD/Banner_Bot.git
   cd Banner_Bot
   ```

2. Установите Ghostscript (системная зависимость):
   ```bash
   # Ubuntu/Debian
   sudo apt-get install ghostscript
   # macOS
   brew install ghostscript
   ```

3. Установите зависимости Python:
   ```bash
   pip install -r requirements.txt
   ```

4. Создайте `.env` в корне проекта:
   ```env
   TELEGRAM_BOT_TOKEN=ваш_токен_бота
   TELEGRAM_CHANNEL_ID=ID_служебного_канала
   ADMIN_TELEGRAM_ID=ваш_ID_в_Telegram
   STARS_PRICE=50
   ```

5. Запустите:
   ```bash
   python -m src.main
   ```

### Вариант 2: Docker (рекомендуется)

1. Создайте `.env` (см. выше)

2. Запустите:
   ```bash
   docker compose up --build -d
   ```

   Ghostscript и ICC-профиль устанавливаются автоматически при сборке образа.

3. Логи:
   ```bash
   docker compose logs -f
   ```

## 🔧 Конфигурация

Все параметры — в `src/config.py`. Переменные окружения через `.env`:

| Переменная | Обязательная | Описание |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | ✅ | Токен бота от @BotFather |
| `TELEGRAM_CHANNEL_ID` | ✅ | ID служебного канала (мониторинг оплат) |
| `ADMIN_TELEGRAM_ID` | — | ID администратора для `/stats` и `/lastorder` |
| `STARS_PRICE` | — | Цена PDF в Telegram Stars (по умолчанию `50`) |
| `ICC_PROFILE_PATH` | — | Путь к ICC-профилю (по умолчанию `/profiles/ISOcoated_v2_300_eci.icc`) |

Константы в `config.py`:

- `MIN_DIMENSION` / `MAX_DIMENSION` — допустимые размеры баннера (500–3000 мм)
- `SAFE_ZONE_MM` — поля безопасности (30 мм)
- `FONTS` — список шрифтов и пути к файлам
- `COLORS` — палитра с RGB (превью) и CMYK (печать) значениями
- `POSTPRINT_OPTIONS` — варианты постпечатной обработки

## 📱 Сценарий использования

1. Отправить `/start`
2. Задать параметры через кнопки меню (на каждом шаге доступен шаблон):
   - Ширина и высота — кнопки типовых размеров или ручной ввод
   - Цвет фона и цвет текста — палитра или готовые цветовые схемы
   - Шрифт (с превью)
   - Текст: количество строк → текст каждой строки (с подсказками слоганов)
   - Масштаб отдельных строк (50–100%)
   - Постпечатная обработка
3. Нажать **🚀 Сгенерировать баннер** → получить JPEG-превью с вотермаркой
4. Подтвердить → выставляется инвойс на оплату Stars
5. После оплаты — PDF отправляется в чат, канал получает карточку заказа

Параметры можно редактировать в любой момент до генерации.

## 🎨 Параметры баннера

**Размеры (шаблоны):** 3×2, 2×1, 1×0.5, 1.5×1, 1.5×0.5 м. Произвольный размер — ручной ввод 500–3000 мм.

**Цвета:** Белый, Чёрный, Красный, Жёлтый, Синий, Зелёный

**Цветовые схемы (шаблоны):** Классика, Энергия, Доверие, Свежесть, Тепло, Премиум

**Шрифты:** Golos Text, Tenor Sans, Fira Sans, Igra Sans

**Постпечать:**
- Без люверсов (`NL`)
- 4 по углам (`4L`)
- Через 0.25м (`PL`)

## 🖨️ Качество PDF для типографии

PDF генерируется в два шага:

1. **ReportLab** — формирует промежуточный `raw.pdf` с CMYK-цветами (v1.4)
2. **Ghostscript** — постобработка → `print_ready.pdf`:
   - Стандарт **PDF/A-1b** (XMP-метаданные, OutputIntent)
   - **ICC-профиль ISOcoated\_v2\_300** встроен как OutputIntent
   - Все шрифты переведены в **кривые** (`-dNoOutputFonts`)
   - Цветовое пространство **CMYK** (`-sColorConversionStrategy=CMYK`)

Файл принимается типографиями без доработки.

## 💳 Монетизация и защита

- Оплата: **Telegram Stars**, цена задаётся через `STARS_PRICE`
- `delivery_log` хранит SHA-256 файла, `tg_message_id` и статус доставки — TTL 14 суток
- Основание хранения `tg_id`: исполнение договора (ст. 6 п. 5 152-ФЗ)
- Служебный канал получает карточку заказа **без ПД** (без имени и username пользователя)

## 🛡️ Администрирование

| Команда | Описание |
|---|---|
| `/stats` | Статистика: пользователи, выручка, заказы, конверсия воронки |
| `/lastorder` | Скачать PDF последнего заказа |

Команды доступны только пользователю с `ADMIN_TELEGRAM_ID`.

## 📦 Volumes (Docker)

| Путь на хосте | Путь в контейнере | Содержимое |
|---|---|---|
| `./orders` | `/app/orders` | PDF-файлы заказов |
| `./bot_data` | `/app/data` | БД SQLite + файл персистентности FSM |

## 📄 Лицензия

MIT — см. файл [LICENSE](LICENSE).
