"""SQLite への接続とスキーマ定義。

このモジュールと同じ repository パッケージの中だけが SQL を書く。routers と
services は repository の関数を通してデータに触る（接続の取得は app/deps.py が
唯一の例外で、そこから依存性として各層に配られる）。
"""

from __future__ import annotations

import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

DEFAULT_DB_PATH = os.environ.get("EXPENSE_DB", "expense.sqlite3")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    role        TEXT NOT NULL CHECK (role IN ('employee', 'manager', 'finance', 'admin')),
    department  TEXT NOT NULL,
    manager_id  INTEGER REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS expenses (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    submitter_id  INTEGER NOT NULL REFERENCES users(id),
    amount_minor  INTEGER NOT NULL,
    currency      TEXT NOT NULL DEFAULT 'JPY',
    category      TEXT NOT NULL,
    description   TEXT NOT NULL,
    incurred_on   TEXT NOT NULL,
    receipt_name  TEXT,
    status        TEXT NOT NULL,
    created_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS approvals (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    expense_id  INTEGER NOT NULL REFERENCES expenses(id),
    step        INTEGER NOT NULL,
    approver_id INTEGER NOT NULL REFERENCES users(id),
    decision    TEXT NOT NULL CHECK (decision IN ('approved', 'rejected')),
    comment     TEXT NOT NULL DEFAULT '',
    decided_at  TEXT NOT NULL,
    UNIQUE (expense_id, step)
);

CREATE TABLE IF NOT EXISTS payments (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    expense_id  INTEGER NOT NULL UNIQUE REFERENCES expenses(id),
    paid_by     INTEGER NOT NULL REFERENCES users(id),
    reference   TEXT NOT NULL,
    paid_at     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS notifications (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    expense_id   INTEGER NOT NULL REFERENCES expenses(id),
    recipient_id INTEGER NOT NULL REFERENCES users(id),
    message      TEXT NOT NULL,
    created_at   TEXT NOT NULL,
    read_at      TEXT
);

CREATE TABLE IF NOT EXISTS audit_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,
    entity_id   INTEGER NOT NULL,
    action      TEXT NOT NULL,
    actor_id    INTEGER NOT NULL,
    detail      TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_expenses_status ON expenses(status);
CREATE INDEX IF NOT EXISTS idx_approvals_expense ON approvals(expense_id);
CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_log(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_notifications_recipient ON notifications(recipient_id, read_at);
"""


def connect(path: str | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(path or DEFAULT_DB_PATH, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """1つの申請に対する状態変更と監査ログを不可分にまとめる。"""
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except Exception:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")
