"""notifications テーブルの読み書き。"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime


def create(
    conn: sqlite3.Connection,
    *,
    expense_id: int,
    recipient_id: int,
    message: str,
) -> None:
    conn.execute(
        """
        INSERT INTO notifications (expense_id, recipient_id, message, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (
            expense_id,
            recipient_id,
            message,
            datetime.now(UTC).isoformat(timespec="seconds"),
        ),
    )


def list_for_user(conn: sqlite3.Connection, recipient_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT * FROM notifications
        WHERE recipient_id = ?
        ORDER BY id DESC
        """,
        (recipient_id,),
    ).fetchall()


def unread_count(conn: sqlite3.Connection, recipient_id: int) -> int:
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM notifications WHERE recipient_id = ? AND read_at IS NULL",
        (recipient_id,),
    ).fetchone()
    return int(row["n"])


def mark_all_read(conn: sqlite3.Connection, recipient_id: int) -> None:
    conn.execute(
        "UPDATE notifications SET read_at = ? WHERE recipient_id = ? AND read_at IS NULL",
        (datetime.now(UTC).isoformat(timespec="seconds"), recipient_id),
    )
