from __future__ import annotations

import json
import sqlite3
import threading
import time
from contextlib import contextmanager

SCHEMA = """
CREATE TABLE IF NOT EXISTS deals (
    deal_id TEXT PRIMARY KEY,
    item_id TEXT,
    item_name TEXT,
    buyer_username TEXT,
    chat_id TEXT,
    status TEXT,
    price REAL,
    created_at REAL,
    confirmed_at REAL,
    rolled_back_at REAL,
    delivered INTEGER DEFAULT 0,
    reminder_sent INTEGER DEFAULT 0,
    raw_json TEXT
);

CREATE TABLE IF NOT EXISTS stats_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT,
    deal_id TEXT,
    amount REAL DEFAULT 0,
    ts REAL
);

CREATE TABLE IF NOT EXISTS autodelivery (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword TEXT NOT NULL,
    match_mode TEXT DEFAULT 'contains',   -- contains / exact / item
    item_id TEXT,                          -- если привязано к конкретному лоту
    response_text TEXT,
    goods_json TEXT,                       -- список уникальных "товаров" для мульти-выдачи (JSON list)
    enabled INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    text TEXT
);

CREATE TABLE IF NOT EXISTS custom_commands (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    command TEXT UNIQUE,
    response_text TEXT,
    enabled INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS auto_responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trigger_event TEXT,     -- new_review / deal_problem / new_deal / welcome ...
    response_text TEXT,
    enabled INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS blacklist (
    username TEXT PRIMARY KEY,
    reason TEXT,
    added_at REAL
);

CREATE TABLE IF NOT EXISTS restore_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id TEXT,
    item_data_json TEXT,
    created_at REAL
);

CREATE TABLE IF NOT EXISTS plugin_licenses (
    plugin_id TEXT PRIMARY KEY,
    license_key TEXT,
    activated_at REAL,
    active INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS kv_store (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS processed_events (
    event_key TEXT PRIMARY KEY,
    ts REAL
);
"""


class Database:
    """Простая потокобезопасная обёртка над SQLite (без ORM, чтобы не тащить лишние зависимости)."""

    def __init__(self, path: str = "data/bot.db"):
        self.path = path
        self._local = threading.local()
        self._lock = threading.RLock()
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn"):
            self._local.conn = sqlite3.connect(self.path, check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    @contextmanager
    def cursor(self):
        with self._lock:
            conn = self._connect()
            cur = conn.cursor()
            try:
                yield cur
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                cur.close()

    # ---------- generic helpers ----------
    def execute(self, sql: str, params: tuple = ()):
        with self.cursor() as cur:
            cur.execute(sql, params)
            return cur.lastrowid

    def fetchone(self, sql: str, params: tuple = ()):
        with self.cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
            return dict(row) if row else None

    def fetchall(self, sql: str, params: tuple = ()):
        with self.cursor() as cur:
            cur.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]

    # ---------- kv store ----------
    def kv_get(self, key: str, default=None):
        row = self.fetchone("SELECT value FROM kv_store WHERE key=?", (key,))
        if not row:
            return default
        try:
            return json.loads(row["value"])
        except Exception:
            return row["value"]

    def kv_set(self, key: str, value):
        self.execute(
            "INSERT INTO kv_store(key, value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, json.dumps(value, ensure_ascii=False)),
        )

    # ---------- idempotency ----------
    def already_processed(self, event_key: str) -> bool:
        row = self.fetchone("SELECT 1 FROM processed_events WHERE event_key=?", (event_key,))
        if row:
            return True
        self.execute(
            "INSERT OR IGNORE INTO processed_events(event_key, ts) VALUES(?,?)",
            (event_key, time.time()),
        )
        return False
