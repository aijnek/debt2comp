"""audit_log テーブルの読み書き。

状態を変えた操作は必ずここに1行残す。書き込みは状態変更と同じトランザクション
の中で行い、片方だけが残る状態を作らない。
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime


def record(
    conn: sqlite3.Connection,
    *,
    entity_type: str,
    entity_id: int,
    action: str,
    actor_id: int,
    detail: str = "",
) -> None:
    conn.execute(
        """
        INSERT INTO audit_log (entity_type, entity_id, action, actor_id, detail, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            entity_type,
            entity_id,
            action,
            actor_id,
            detail,
            datetime.now(UTC).isoformat(timespec="seconds"),
        ),
    )


def list_for(
    conn: sqlite3.Connection, entity_type: str, entity_id: int
) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT a.*, u.name AS actor_name
        FROM audit_log a
        JOIN users u ON u.id = a.actor_id
        WHERE a.entity_type = ? AND a.entity_id = ?
        ORDER BY a.id
        """,
        (entity_type, entity_id),
    ).fetchall()


def recent(conn: sqlite3.Connection, limit: int = 50) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT a.*, u.name AS actor_name
        FROM audit_log a
        JOIN users u ON u.id = a.actor_id
        ORDER BY a.id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
