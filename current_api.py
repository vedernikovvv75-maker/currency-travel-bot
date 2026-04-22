import os
from typing import Optional

import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("CURRENCY_API_KEY")
BASE_URL = "https://api.exchangerate.host"

# Учебная карта стран -> валют (можно расширять по мере необходимости).
COUNTRY_TO_CURRENCY = {
    "russia": "RUB",
    "russian federation": "RUB",
    "россия": "RUB",
    "italy": "EUR",
    "италия": "EUR",
    "china": "CNY",
    "китай": "CNY",
    "usa": "USD",
    "united states": "USD",
    "сша": "USD",
    "japan": "JPY",
    "япония": "JPY",
    "great britain": "GBP",
    "united kingdom": "GBP",
    "uk": "GBP",
    "великобритания": "GBP",
}


class CurrencyApiError(Exception):
    pass


def resolve_currency_by_country(country: str) -> Optional[str]:
    if not country:
        return None
    return COUNTRY_TO_CURRENCY.get(country.strip().lower())


def _safe_get(url: str, params: dict) -> dict:
    if not API_KEY:
        raise CurrencyApiError("Не найден CURRENCY_API_KEY в переменных окружения.")

    try:
        response = requests.get(url, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        raise CurrencyApiError(f"Ошибка сети при обращении к API: {exc}") from exc
    except ValueError as exc:
        raise CurrencyApiError("API вернул некорректный JSON.") from exc

    if isinstance(data, dict) and data.get("success") is False:
        info = data.get("error", {}).get("info", "Неизвестная ошибка API.")
        raise CurrencyApiError(f"Ошибка API: {info}")

    return data


def get_current_rate(source: str = "USD", currencies: Optional[list[str]] = None) -> dict:
    if currencies is None:
        currencies = ["EUR", "GBP", "JPY"]

    url = f"{BASE_URL}/live"
    params = {
        "access_key": API_KEY,
        "source": source.upper(),
        "currencies": ",".join([c.upper() for c in currencies]),
    }
    return _safe_get(url, params)


def convert_currency(amount: float, from_currency: str, to_currency: str) -> dict:
    url = f"{BASE_URL}/convert"
    params = {
        "access_key": API_KEY,
        "from": from_currency.upper(),
        "to": to_currency.upper(),
        "amount": amount,
    }
    return _safe_get(url, params)


def extract_converted_amount(payload: dict) -> float:
    result = payload.get("result")
    if result is not None:
        return float(result)

    query = payload.get("query", {})
    info = payload.get("info", {})
    amount = query.get("amount")
    rate = info.get("quote")
    if amount is not None and rate is not None:
        return float(amount) * float(rate)

    raise CurrencyApiError("Не удалось извлечь результат конвертации из ответа API.")


if __name__ == "__main__":
    print(get_current_rate(source="RUB", currencies=["USD", "EUR", "CNY"]))
    print(convert_currency(100, "USD", "EUR"))
