# Методичка: Финансовый Telegram-бот для путешествий

Короткий практический гайд по сборке учебного проекта: бот для учета расходов в поездках с конвертацией валют через `exchangerate.host`.

---

## 1) Цель проекта

Собрать Telegram-бота, который:

- создает путешествия с валютной парой (страна выезда -> страна назначения);
- конвертирует стартовый бюджет;
- учитывает траты в валюте страны пребывания;
- показывает остаток в двух валютах;
- хранит данные в SQLite.

---

## 2) Минимальные требования

- Python 3.10+
- Cursor / VS Code
- Telegram-бот (токен от `@BotFather`)
- API-ключ `exchangerate.host`

---

## 3) Быстрый старт (Windows)

### 3.1 Создать и активировать окружение

```bash
python -m venv venv
venv\Scripts\activate
```

Проверка: в терминале есть префикс `(venv)`.

### 3.2 Создать базовые файлы

- `current_api.py`
- `requirements.txt`
- `EnvExample`

### 3.3 Заполнить `requirements.txt`

```text
requests
python-dotenv
pytelegrambotapi
```

### 3.4 Установить зависимости

```bash
pip install -r requirements.txt
```

---

## 4) Безопасность ключей (обязательно)

> API-ключи и токены не храним в коде.

### 4.1 Пример `EnvExample`

```env
TELEGRAM_BOT_TOKEN=your_telegram_token
CURRENCY_API_KEY=your_currency_api_key
```

### 4.2 Загрузка переменных в Python

```python
import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CURRENCY_API_KEY = os.getenv("CURRENCY_API_KEY")
```

---

## 5) Модуль API (`current_api.py`)

### 5.1 Получение текущих курсов

```python
import os
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("CURRENCY_API_KEY")


def get_current_rate(source: str = "USD", currencies: list[str] | None = None) -> dict:
    if currencies is None:
        currencies = ["EUR", "GBP", "JPY"]

    url = "https://api.exchangerate.host/live"
    params = {
        "access_key": API_KEY,
        "source": source,
        "currencies": ",".join(currencies),
    }
    response = requests.get(url, params=params, timeout=20)
    response.raise_for_status()
    return response.json()
```

### 5.2 Конвертация суммы

```python
def convert_currency(amount: float, from_currency: str, to_currency: str) -> dict:
    url = "https://api.exchangerate.host/convert"
    params = {
        "access_key": API_KEY,
        "from": from_currency,
        "to": to_currency,
        "amount": amount,
    }
    response = requests.get(url, params=params, timeout=20)
    response.raise_for_status()
    return response.json()
```

### 5.3 Локальный тест

```python
if __name__ == "__main__":
    print(get_current_rate(source="RUB", currencies=["USD", "EUR", "CNY"]))
    print(convert_currency(100, "USD", "EUR"))
```

---

## 6) Функциональные требования к боту

### 6.1 Главное меню (inline)

- Создать новое путешествие
- Мои путешествия
- Баланс
- История расходов
- Изменить курс

### 6.2 Слэш-команды (как альтернатива)

- `/start`
- `/newtrip`
- `/switch`
- `/balance`
- `/history`
- `/setrate`

### 6.3 Логика расходов

- любое число от пользователя = трата в валюте страны пребывания;
- показать пересчет в домашнюю валюту;
- спросить подтверждение: учесть расход или нет;
- при подтверждении сохранить расход и обновить баланс.

---

## 7) Структура данных (минимум)

Рекомендуемые сущности SQLite:

- `users` — пользователь Telegram;
- `trips` — путешествия пользователя;
- `expenses` — расходы по путешествиям.

Минимальные поля:

- `trips`: `id`, `user_id`, `title`, `home_currency`, `target_currency`, `rate`, `balance_home`, `balance_target`, `is_active`;
- `expenses`: `id`, `trip_id`, `amount_target`, `amount_home`, `created_at`, `comment`.

---

## 8) Чеклист тестирования

###! Базовые проверки

- [ ] Бот отвечает на `/start`
- [ ] Создается новое путешествие
- [ ] Корректно определяется валютная пара
- [ ] Стартовая сумма конвертируется и сохраняется

###! Проверки расходов

- [ ] Число в чате распознается как сумма расхода
- [ ] Пересчет валют корректный
- [ ] После подтверждения баланс уменьшается
- [ ] Запись появляется в истории

###! Негативные сценарии

- [ ] Введен нечисловой текст -> дружелюбная ошибка
- [ ] Ошибка API -> понятное сообщение
- [ ] Нет активного путешествия -> подсказка пользователю

---

## 9) Частые ошибки и решения

- **Бот не отвечает** -> проверить `TELEGRAM_BOT_TOKEN`, перезапустить приложение.
- **Ошибка импорта** -> убедиться, что активирован `venv` и пакеты установлены.
- **Пустой/ошибочный ответ API** -> проверить `CURRENCY_API_KEY`, лимиты тарифа, интернет.
- **Неверный расчет** -> проверить направление конвертации (`from`/`to`) и сохраняемый курс.

---

## 10) Критерии сдачи домашки

Проект считается готовым, если:

- бот конвертирует валюты через API `exchangerate.host`;
- хранит путешествия, балансы и расходы в SQLite;
- корректно работает как минимум с `/start` и `/newtrip`;
- показывает остатки в двух валютах;
- обрабатывает ошибки ввода и API без падений.

---

## 11) Что можно улучшить после сдачи

- категории расходов (еда, транспорт, жилье);
- лимиты и уведомления по бюджету;
- графики расходов;
- несколько валют в одном путешествии;
- более умная аналитика истории.

---

## Короткий итог

Если следовать шагам из этой методички, можно быстро собрать рабочий учебный проект: Telegram-бот + API курсов + SQLite + безопасная конфигурация через переменные окружения.
