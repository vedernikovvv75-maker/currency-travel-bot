# Currency Travel Bot

**Travel wallet in Telegram**: создавайте поездки, фиксируйте расходы в локальной валюте и сразу видьте остаток в двух валютах.

Проект помогает путешественнику контролировать бюджет без таблиц и ручных пересчетов. Курсы подтягиваются через `exchangerate.host`, данные пользователя хранятся локально в SQLite.

## Product Pitch

Пользователь открывает бота, создает путешествие (`Россия -> Италия`), вводит стартовую сумму в домашней валюте и сразу получает эквивалент в валюте поездки.  
Далее отправляет любые суммы трат обычными сообщениями, а бот:

- пересчитывает сумму в домашнюю валюту;
- предлагает подтверждение расхода кнопками;
- сохраняет операцию в историю;
- обновляет баланс в обеих валютах.

## Why This Product

- **Zero-friction UX** — расходы можно вводить как обычный текст (`125.5`), без сложных форм.
- **Dual-currency control** — баланс одновременно в валюте поездки и домашней валюте.
- **Trip-based structure** — несколько поездок на пользователя, быстрое переключение между ними.
- **Safe config** — токены и ключи берутся из переменных окружения через `load_dotenv()`.
- **MVP-ready architecture** — модульная структура для быстрого роста продукта.

## Core Features

- создание нового путешествия с валютной парой;
- автоматическое определение валюты по стране (базовый словарь);
- конвертация бюджета и расходов через API;
- ручное изменение курса (например, курс обменника на месте);
- история расходов по активному путешествию;
- inline-меню + slash-команды для навигации.

## User Flow

1. `/start` -> главное меню.
2. `Создать новое путешествие` -> страна выезда -> страна назначения.
3. Бот показывает курс и предлагает подтвердить или ввести вручную.
4. Пользователь вводит стартовый бюджет.
5. Любое число в чате = потенциальный расход.
6. `✅ Да` -> расход сохранен, баланс обновлен.

## Commands

- `/start` — вход в бота и меню
- `/newtrip` — запуск сценария создания поездки
- `/switch` — список поездок и выбор активной
- `/balance` — текущий остаток
- `/history` — последние расходы
- `/setrate` — ручная корректировка курса

## Tech Stack

- Python 3.10+
- [pytelegrambotapi](https://github.com/eternnoir/pyTelegramBotAPI)
- [requests](https://pypi.org/project/requests/)
- [python-dotenv](https://pypi.org/project/python-dotenv/)
- SQLite
- [exchangerate.host](https://exchangerate.host/)

## Project Structure

```text
currency-travel-bot/
├─ bot.py
├─ current_api.py
├─ database.py
├─ requirements.txt
├─ .env.example
├─ travel_finance_bot_lesson.md
└─ travel_finance_bot_methodical_guide.md
```

## Quick Start (Windows)

```bash
git clone <YOUR_REPO_URL>
cd currency-travel-bot
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Создайте `.env` по образцу `.env.example`:

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
CURRENCY_API_KEY=your_currency_api_key
```

Запуск:

```bash
python bot.py
```

## Environment Variables

- `TELEGRAM_BOT_TOKEN` — токен бота от `@BotFather`
- `CURRENCY_API_KEY` — ключ `exchangerate.host`

> `.env` хранится локально и не коммитится. В репозитории оставляйте только `.env.example`.

## MVP Limits

- словарь стран/валют пока базовый;
- нет категорий расходов;
- нет экспорта отчетов.

## Product Roadmap

- расширенный country/currency mapping;
- категории расходов;
- экспорт в CSV;
- бюджетные лимиты и уведомления;
- аналитика и отчеты по поездкам.

## License

Учебный проект. При публикации в open source рекомендуется добавить `LICENSE` (например, MIT).
