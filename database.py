import sqlite3
from pathlib import Path
from typing import Any, Optional

DB_PATH = Path(__file__).resolve().parent / "travel_bot.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS trips (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                home_currency TEXT NOT NULL,
                target_currency TEXT NOT NULL,
                rate REAL NOT NULL,
                balance_home REAL NOT NULL,
                balance_target REAL NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY,
                trip_id INTEGER NOT NULL,
                amount_target REAL NOT NULL,
                amount_home REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                comment TEXT,
                FOREIGN KEY(trip_id) REFERENCES trips(id)
            )
            """
        )


def ensure_user(telegram_id: int, username: Optional[str]) -> int:
    with get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO users(telegram_id, username) VALUES(?, ?)",
            (telegram_id, username),
        )
        conn.execute(
            "UPDATE users SET username = ? WHERE telegram_id = ?",
            (username, telegram_id),
        )
        row = conn.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,)).fetchone()
        return int(row["id"])


def create_trip(
    user_id: int,
    title: str,
    home_currency: str,
    target_currency: str,
    rate: float,
    balance_home: float,
    balance_target: float,
) -> int:
    with get_connection() as conn:
        conn.execute("UPDATE trips SET is_active = 0 WHERE user_id = ?", (user_id,))
        cur = conn.execute(
            """
            INSERT INTO trips(user_id, title, home_currency, target_currency, rate, balance_home, balance_target, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (user_id, title, home_currency, target_currency, rate, balance_home, balance_target),
        )
        return int(cur.lastrowid)


def get_user_trips(user_id: int) -> list[sqlite3.Row]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM trips WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
        return list(rows)


def set_active_trip(user_id: int, trip_id: int) -> None:
    with get_connection() as conn:
        conn.execute("UPDATE trips SET is_active = 0 WHERE user_id = ?", (user_id,))
        conn.execute("UPDATE trips SET is_active = 1 WHERE user_id = ? AND id = ?", (user_id, trip_id))


def get_active_trip(user_id: int) -> Optional[sqlite3.Row]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM trips WHERE user_id = ? AND is_active = 1 LIMIT 1",
            (user_id,),
        ).fetchone()
        return row


def update_trip_rate(user_id: int, trip_id: int, rate: float) -> None:
    with get_connection() as conn:
        conn.execute("UPDATE trips SET rate = ? WHERE user_id = ? AND id = ?", (rate, user_id, trip_id))


def add_expense(trip_id: int, amount_target: float, amount_home: float, comment: str = "") -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO expenses(trip_id, amount_target, amount_home, comment) VALUES(?, ?, ?, ?)",
            (trip_id, amount_target, amount_home, comment),
        )
        conn.execute(
            """
            UPDATE trips
            SET balance_target = balance_target - ?,
                balance_home = balance_home - ?
            WHERE id = ?
            """,
            (amount_target, amount_home, trip_id),
        )


def get_trip_expenses(trip_id: int, limit: int = 20) -> list[sqlite3.Row]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM expenses
            WHERE trip_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (trip_id, limit),
        ).fetchall()
        return list(rows)


def row_to_dict(row: Any) -> dict:
    return dict(row) if row is not None else {}
