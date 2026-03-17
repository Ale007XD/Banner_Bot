# Banner Bot

Telegram-бот для генерации печатных баннеров. Принимает параметры через интерактивный диалог, формирует JPEG-превью и PDF-файл, готовый для передачи в типографию.

## 📋 Возможности

- Настройка размеров баннера (ширина и высота в мм, от 500 до 3000)
- Выбор цвета фона и текста из палитры
- Выбор шрифта с визуальным превью
- Ввод до 4 строк текста с индивидуальным масштабированием каждой строки
- Редактирование текста после ввода
- Выбор постпечатной обработки (люверсы)
- JPEG-превью перед финальной генерацией
- PDF для типографии: **CMYK, ICC-профиль ISOcoated_v2\_300, шрифты в кривых, PDF/A-1b**
- Отправка готового PDF в Telegram-канал с карточкой заказа
- Нумерация заказов в формате `ДА-ДДММ-NNN`
- Сохранение состояния диалога между перезапусками (PicklePersistence)

## 🛠️ Технологии

| Компонент | Назначение |
|---|---|
| Python 3.10 | Основной язык |
| [python-telegram-bot 21](https://github.com/python-telegram-bot/python-telegram-bot) | Telegram Bot API, FSM (ConversationHandler) |
| [Pillow](https://python-pillow.org/) | Генерация JPEG-превью |
| [ReportLab](https://www.reportlab.com/) | Генерация промежуточного PDF |
| [Ghostscript](https://www.ghostscript.com/) | Постобработка: PDF/A-1b, CMYK+ICC, шрифты в кривых |
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
│   ├── banner_generator.py  # JPEG-превью + двухшаговая генерация PDF
│   ├── bot_handlers.py      # FSM-обработчики диалога
│   ├── config.py            # Все константы: цвета, шрифты, состояния FSM
│   ├── main.py              # Точка входа, PicklePersistence, регистрация хендлеров
│   └── order_manager.py     # Счётчик заказов (thread-safe)
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
   TELEGRAM_CHANNEL_ID=ID_канала_для_отправки_баннеров
   ADMIN_TELEGRAM_ID=ваш_ID_в_Telegram
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
| `TELEGRAM_CHANNEL_ID` | ✅ | ID канала для отправки PDF |
| `ADMIN_TELEGRAM_ID` | — | ID администратора для `/stats` и `/lastorder` |
| `ICC_PROFILE_PATH` | — | Путь к ICC-профилю (по умолчанию `/profiles/ISOcoated_v2_300_eci.icc`) |

Константы в `config.py`:

- `MIN_DIMENSION` / `MAX_DIMENSION` — допустимые размеры баннера (500–3000 мм)
- `SAFE_ZONE_MM` — поля безопасности (30 мм)
- `FONTS` — список шрифтов и пути к файлам
- `COLORS` — палитра с RGB (превью) и CMYK (печать) значениями
- `POSTPRINT_OPTIONS` — варианты постпечатной обработки

## 📱 Сценарий использования

1. Отправить `/start`
2. Последовательно задать параметры через кнопки меню:
   - Ширина и высота (мм)
   - Цвет фона и цвет текста
   - Шрифт (с превью)
   - Текст: количество строк → текст каждой строки
   - Масштаб отдельных строк (50–100%)
   - Постпечатная обработка
3. Нажать **🚀 Сгенерировать баннер** → получить JPEG-превью
4. Подтвердить → PDF отправится в канал

Параметры можно редактировать в любой момент до генерации.

## 🎨 Параметры баннера

**Размеры:** 500–3000 мм по каждой стороне

**Цвета:** Белый, Чёрный, Красный, Жёлтый, Синий, Зелёный

**Шрифты:** Golos Text, Tenor Sans, Fira Sans, Igra Sans

**Постпечать:**
- Без люверсов (`NL`)
- 4 по углам (`4L`)
- Через 0.25м (`PL`)

## 🖨️ Качество PDF для типографии

PDF генерируется в два шага:

1. **ReportLab** — формирует промежуточный PDF с CMYK-цветами
2. **Ghostscript** — постобработка:
   - Стандарт **PDF/A-1b** (XMP-метаданные, OutputIntent)
   - **ICC-профиль ISOcoated\_v2\_300** встроен как OutputIntent
   - Все шрифты переведены в **кривые** (`-dNoOutputFonts`)

Файл проходит валидацию и принимается типографиями без доработки.

## 🛡️ Администрирование

| Команда | Описание |
|---|---|
| `/stats` | Статистика заказов (сегодня / всего / топ-5 дней) |
| `/lastorder` | Скачать PDF последнего заказа |

Команды доступны только пользователю с `ADMIN_TELEGRAM_ID`.

## 📦 Volumes (Docker)

| Путь на хосте | Путь в контейнере | Содержимое |
|---|---|---|
| `./orders` | `/app/orders` | PDF-файлы заказов |
| `./bot_data` | `/app/data` | Файл персистентности FSM (`bot_persistence.pickle`) |
| `./order_counter.json` | `/app/order_counter.json` | Счётчик заказов |

## 📄 Лицензия

MIT — см. файл [LICENSE](LICENSE).
