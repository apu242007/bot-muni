import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

DB_PATH=Path('bot_sqlite3')

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        phone VARCHAR PRIMARY KEY,
        name VARCHAR(20),
        last_seen TEXT,
        state TEXT DEFAULT 'idle',
        context_json TEXT DEFAULT '{}'
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone VARCHAR(15),
        direction TEXT, -- in/out
        text TEXT,
        ts TEXT
    );
    """)

    conn.commit()
    conn.close()


def upsert_user(phone: str):
    conn = get_conn()
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()
    cur.execute("""
    INSERT INTO users(phone, last_seen) VALUES(?, ?)
    ON CONFLICT(phone) DO UPDATE SET last_seen=excluded.last_seen;
    """, (phone, now))
    conn.commit()
    conn.close()

def set_state(phone: str, state: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET state=? WHERE phone=?", (state, phone))
    conn.commit()
    conn.close()

def get_state(phone: str) -> str:
    conn = get_conn()
    cur = conn.cursor()
    row = cur.execute("SELECT state FROM users WHERE phone=?", (phone,)).fetchone()
    conn.close()
    return row["state"] if row else "idle"

def log_message(phone: str, direction: str, text: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("INSERT INTO messages(phone, direction, text, ts) VALUES(?,?,?,datetime('now'))",
                (phone, direction, text))
    conn.commit()
    conn.close()


# app/db.py (agregar)
import json

def get_context(phone: str) -> dict:
    conn = get_conn()
    cur = conn.cursor()
    row = cur.execute("SELECT context_json FROM users WHERE phone=?", (phone,)).fetchone()
    conn.close()
    if not row:
        return {}
    try:
        return json.loads(row["context_json"] or "{}")
    except:
        return {}

def set_context(phone: str, ctx: dict):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("UPDATE users SET context_json=? WHERE phone=?",
                (json.dumps(ctx, ensure_ascii=False), phone))
    conn.commit()
    conn.close()