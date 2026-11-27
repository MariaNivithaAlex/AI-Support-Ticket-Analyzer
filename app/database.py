from __future__ import annotations

import os
import sqlite3
from pathlib import Path

DB_PATH = Path(os.getenv("TICKET_DB_PATH", Path(__file__).resolve().parent.parent / "tickets.db"))


def connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with connect() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_name TEXT NOT NULL,
                email TEXT NOT NULL,
                subject TEXT NOT NULL,
                description TEXT NOT NULL,
                category TEXT NOT NULL,
                priority TEXT NOT NULL,
                sentiment TEXT NOT NULL,
                confidence REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'Open',
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
                updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
            )
        """)
        db.execute("CREATE INDEX IF NOT EXISTS idx_tickets_created_at ON tickets(created_at DESC)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status)")
