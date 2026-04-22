import os
from typing import Optional

import telebot
from dotenv import load_dotenv
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from current_api import (
    CurrencyApiError,
    convert_currency,
    extract_converted_amount,
    resolve_currency_by_country,
)
from database import (
    add_expense,
    create_trip,
    ensure_user,
    get_active_trip,
    get_trip_expenses,
    get_user_trips,
    init_db,
    set_active_trip,
    update_trip_rate,
)

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("Не найден TELEGRAM_BOT_TOKEN. Заполните .env по примеру EnvExample.")

bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

# Временное состояние диалогов по пользователям.
pending_expenses: dict[int, dict] = {}
trip_flow_state: dict[int, dict] = {}


def main_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("Создать новое путешествие", callback_data="newtrip"))
    kb.add(InlineKeyboardButton("Мои путешествия", callback_data="mytrips"))
    kb.add(InlineKeyboardButton("Баланс", callback_data="balance"))
    kb.add(InlineKeyboardButton("История расходов", callback_data="history"))
    kb.add(InlineKeyboardButton("Изменить курс", callback_data="setrate"))
    return kb


def format_balance(trip) -> str:
    return (
        f"Активное путешествие: <b>{trip['title']}</b>\n"
        f"Остаток: <b>{trip['balance_target']:.2f} {trip['target_currency']}</b>\n"
        f"~ <b>{trip['balance_home']:.2f} {trip['home_currency']}</b>\n"
        f"Текущий курс: 1 {trip['target_currency']} = {trip['rate']:.4f} {trip['home_currency']}"
    )


def start_new_trip_flow(message: Message, user_id: int) -> None:
    trip_flow_state[user_id] = {}
    msg = bot.send_message(
        message.chat.id,
        "Введите страну выезда (например: Россия):",
    )
    bot.register_next_step_handler(msg, process_home_country, user_id)


def process_home_country(message: Message, user_id: int) -> None:
    country = message.text.strip()
    currency = resolve_currency_by_country(country)
    if not currency:
        msg = bot.send_message(
            message.chat.id,
            "Не смог определить валюту этой страны. Попробуйте еще раз (например: Россия, Италия, Китай, США).",
        )
        bot.register_next_step_handler(msg, process_home_country, user_id)
        return

    trip_flow_state[user_id]["home_country"] = country
    trip_flow_state[user_id]["home_currency"] = currency
    msg = bot.send_message(message.chat.id, "Введите страну назначения (например: Италия):")
    bot.register_next_step_handler(msg, process_target_country, user_id)


def process_target_country(message: Message, user_id: int) -> None:
    country = message.text.strip()
    currency = resolve_currency_by_country(country)
    if not currency:
        msg = bot.send_message(
            message.chat.id,
            "Не смог определить валюту этой страны. Попробуйте еще раз.",
        )
        bot.register_next_step_handler(msg, process_target_country, user_id)
        return

    state = trip_flow_state.get(user_id, {})
    home_currency = state["home_currency"]
    target_currency = currency

    try:
        data = convert_currency(1, target_currency, home_currency)
        rate = extract_converted_amount(data)
    except CurrencyApiError as exc:
        bot.send_message(message.chat.id, f"Не удалось получить курс: {exc}")
        return

    state["target_country"] = country
    state["target_currency"] = target_currency
    state["rate"] = rate
    trip_flow_state[user_id] = state

    msg = bot.send_message(
        message.chat.id,
        (
            f"Курс найден: 1 {target_currency} = {rate:.4f} {home_currency}\n"
            "Подходит курс? Ответьте: да / нет"
        ),
    )
    bot.register_next_step_handler(msg, process_rate_confirmation, user_id)


def process_rate_confirmation(message: Message, user_id: int) -> None:
    answer = message.text.strip().lower()
    if answer in ("да", "yes", "y", "ok"):
        msg = bot.send_message(message.chat.id, "Введите начальную сумму в домашней валюте:")
        bot.register_next_step_handler(msg, process_initial_amount, user_id)
        return

    if answer in ("нет", "no", "n"):
        msg = bot.send_message(
            message.chat.id,
            "Введите курс вручную в формате: сколько домашней валюты за 1 валюту назначения (например 104.5):",
        )
        bot.register_next_step_handler(msg, process_manual_rate, user_id)
        return

    msg = bot.send_message(message.chat.id, "Пожалуйста, ответьте 'да' или 'нет'.")
    bot.register_next_step_handler(msg, process_rate_confirmation, user_id)


def process_manual_rate(message: Message, user_id: int) -> None:
    try:
        rate = float(message.text.replace(",", ".").strip())
        if rate <= 0:
            raise ValueError
    except ValueError:
        msg = bot.send_message(message.chat.id, "Курс должен быть положительным числом. Попробуйте еще раз:")
        bot.register_next_step_handler(msg, process_manual_rate, user_id)
        return

    trip_flow_state[user_id]["rate"] = rate
    msg = bot.send_message(message.chat.id, "Введите начальную сумму в домашней валюте:")
    bot.register_next_step_handler(msg, process_initial_amount, user_id)


def process_initial_amount(message: Message, user_id: int) -> None:
    try:
        amount_home = float(message.text.replace(",", ".").strip())
        if amount_home <= 0:
            raise ValueError
    except ValueError:
        msg = bot.send_message(message.chat.id, "Сумма должна быть положительным числом. Попробуйте еще раз:")
        bot.register_next_step_handler(msg, process_initial_amount, user_id)
        return

    state = trip_flow_state.get(user_id, {})
    home_currency = state["home_currency"]
    target_currency = state["target_currency"]
    rate = float(state["rate"])

    amount_target = amount_home / rate
    title = f"{state['home_country']} -> {state['target_country']}"
    trip_id = create_trip(
        user_id=user_id,
        title=title,
        home_currency=home_currency,
        target_currency=target_currency,
        rate=rate,
        balance_home=amount_home,
        balance_target=amount_target,
    )
    trip_flow_state.pop(user_id, None)

    bot.send_message(
        message.chat.id,
        (
            f"Путешествие создано (ID: {trip_id}).\n"
            f"Стартовый баланс: {amount_target:.2f} {target_currency} ~ {amount_home:.2f} {home_currency}"
        ),
        reply_markup=main_menu(),
    )


def show_my_trips(chat_id: int, user_id: int) -> None:
    trips = get_user_trips(user_id)
    if not trips:
        bot.send_message(chat_id, "У вас пока нет путешествий. Создайте первое.", reply_markup=main_menu())
        return

    kb = InlineKeyboardMarkup()
    for trip in trips:
        prefix = "✅ " if trip["is_active"] else ""
        kb.add(InlineKeyboardButton(f"{prefix}{trip['title']}", callback_data=f"switch:{trip['id']}"))
    bot.send_message(chat_id, "Ваши путешествия (нажмите, чтобы сделать активным):", reply_markup=kb)


def show_balance(chat_id: int, user_id: int) -> None:
    trip = get_active_trip(user_id)
    if not trip:
        bot.send_message(chat_id, "Нет активного путешествия. Создайте или выберите существующее.")
        return
    bot.send_message(chat_id, format_balance(trip), reply_markup=main_menu())


def show_history(chat_id: int, user_id: int) -> None:
    trip = get_active_trip(user_id)
    if not trip:
        bot.send_message(chat_id, "Нет активного путешествия.")
        return

    expenses = get_trip_expenses(trip["id"], limit=15)
    if not expenses:
        bot.send_message(chat_id, "История расходов пока пустая.")
        return

    lines = [f"История расходов: <b>{trip['title']}</b>"]
    for exp in expenses:
        lines.append(
            f"- {exp['created_at']}: {exp['amount_target']:.2f} {trip['target_currency']} "
            f"(~ {exp['amount_home']:.2f} {trip['home_currency']})"
        )
    bot.send_message(chat_id, "\n".join(lines), reply_markup=main_menu())


def start_set_rate_flow(message: Message, user_id: int) -> None:
    trip = get_active_trip(user_id)
    if not trip:
        bot.send_message(message.chat.id, "Нет активного путешествия.")
        return

    msg = bot.send_message(
        message.chat.id,
        (
            f"Текущий курс: 1 {trip['target_currency']} = {trip['rate']:.4f} {trip['home_currency']}\n"
            "Введите новый курс:"
        ),
    )
    bot.register_next_step_handler(msg, process_new_rate, user_id, trip["id"])


def process_new_rate(message: Message, user_id: int, trip_id: int) -> None:
    try:
        new_rate = float(message.text.replace(",", ".").strip())
        if new_rate <= 0:
            raise ValueError
    except ValueError:
        msg = bot.send_message(message.chat.id, "Курс должен быть положительным числом. Введите снова:")
        bot.register_next_step_handler(msg, process_new_rate, user_id, trip_id)
        return

    update_trip_rate(user_id, trip_id, new_rate)
    bot.send_message(message.chat.id, f"Курс обновлен: {new_rate:.4f}", reply_markup=main_menu())


def parse_amount(text: str) -> Optional[float]:
    normalized = text.replace(",", ".").strip()
    try:
        value = float(normalized)
        if value > 0:
            return value
    except ValueError:
        return None
    return None


@bot.message_handler(commands=["start"])
def cmd_start(message: Message) -> None:
    user_id = ensure_user(message.from_user.id, message.from_user.username)
    bot.send_message(
        message.chat.id,
        (
            "Привет! Я финансовый помощник для путешествий.\n"
            "Создавайте поездки, считайте расходы и следите за остатком в двух валютах."
        ),
        reply_markup=main_menu(),
    )
    if not get_active_trip(user_id):
        bot.send_message(message.chat.id, "Начнем? Нажмите «Создать новое путешествие».")


@bot.message_handler(commands=["newtrip"])
def cmd_newtrip(message: Message) -> None:
    user_id = ensure_user(message.from_user.id, message.from_user.username)
    start_new_trip_flow(message, user_id)


@bot.message_handler(commands=["switch"])
def cmd_switch(message: Message) -> None:
    user_id = ensure_user(message.from_user.id, message.from_user.username)
    show_my_trips(message.chat.id, user_id)


@bot.message_handler(commands=["balance"])
def cmd_balance(message: Message) -> None:
    user_id = ensure_user(message.from_user.id, message.from_user.username)
    show_balance(message.chat.id, user_id)


@bot.message_handler(commands=["history"])
def cmd_history(message: Message) -> None:
    user_id = ensure_user(message.from_user.id, message.from_user.username)
    show_history(message.chat.id, user_id)


@bot.message_handler(commands=["setrate"])
def cmd_setrate(message: Message) -> None:
    user_id = ensure_user(message.from_user.id, message.from_user.username)
    start_set_rate_flow(message, user_id)


@bot.callback_query_handler(func=lambda c: True)
def on_callback(call) -> None:
    user_id = ensure_user(call.from_user.id, call.from_user.username)
    data = call.data

    if data == "newtrip":
        bot.answer_callback_query(call.id)
        start_new_trip_flow(call.message, user_id)
        return
    if data == "mytrips":
        bot.answer_callback_query(call.id)
        show_my_trips(call.message.chat.id, user_id)
        return
    if data == "balance":
        bot.answer_callback_query(call.id)
        show_balance(call.message.chat.id, user_id)
        return
    if data == "history":
        bot.answer_callback_query(call.id)
        show_history(call.message.chat.id, user_id)
        return
    if data == "setrate":
        bot.answer_callback_query(call.id)
        start_set_rate_flow(call.message, user_id)
        return

    if data.startswith("switch:"):
        trip_id = int(data.split(":")[1])
        set_active_trip(user_id, trip_id)
        bot.answer_callback_query(call.id, "Активное путешествие обновлено.")
        show_balance(call.message.chat.id, user_id)
        return

    if data.startswith("expense_confirm:"):
        amount_target = float(data.split(":")[1])
        p = pending_expenses.get(user_id)
        if not p:
            bot.answer_callback_query(call.id, "Сессия расхода устарела.")
            return
        add_expense(p["trip_id"], amount_target, p["amount_home"], comment="Расход из чата")
        pending_expenses.pop(user_id, None)
        bot.answer_callback_query(call.id, "Расход сохранен.")
        show_balance(call.message.chat.id, user_id)
        return

    if data == "expense_cancel":
        pending_expenses.pop(user_id, None)
        bot.answer_callback_query(call.id, "Расход отменен.")
        bot.send_message(call.message.chat.id, "Не учитываю расход.", reply_markup=main_menu())


@bot.message_handler(func=lambda m: True, content_types=["text"])
def handle_text(message: Message) -> None:
    user_id = ensure_user(message.from_user.id, message.from_user.username)
    amount_target = parse_amount(message.text)
    if amount_target is None:
        bot.send_message(
            message.chat.id,
            "Я понимаю команды и суммы расходов. Отправьте число, например: 125.50",
            reply_markup=main_menu(),
        )
        return

    trip = get_active_trip(user_id)
    if not trip:
        bot.send_message(message.chat.id, "Сначала создайте путешествие: /newtrip")
        return

    amount_home = amount_target * float(trip["rate"])
    pending_expenses[user_id] = {
        "trip_id": int(trip["id"]),
        "amount_home": amount_home,
    }

    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton("✅ Да", callback_data=f"expense_confirm:{amount_target}"),
        InlineKeyboardButton("❌ Нет", callback_data="expense_cancel"),
    )
    bot.send_message(
        message.chat.id,
        (
            f"{amount_target:.2f} {trip['target_currency']} = {amount_home:.2f} {trip['home_currency']}\n"
            "Учесть как расход?"
        ),
        reply_markup=kb,
    )


def run() -> None:
    init_db()
    print("Бот запущен...")
    bot.infinity_polling(skip_pending=True)


if __name__ == "__main__":
    run()
