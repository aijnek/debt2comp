"""users テーブルの読み書き。"""

from __future__ import annotations

import sqlite3

ROLES = ("employee", "manager", "finance", "admin")


def get(conn: sqlite3.Connection, user_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def list_all(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute("SELECT * FROM users ORDER BY id").fetchall()


def list_by_role(conn: sqlite3.Connection, role: str) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM users WHERE role = ? ORDER BY id", (role,)
    ).fetchall()


def manager_of(conn: sqlite3.Connection, user_id: int) -> sqlite3.Row | None:
    return conn.execute(
        """
        SELECT m.* FROM users u
        JOIN users m ON m.id = u.manager_id
        WHERE u.id = ?
        """,
        (user_id,),
    ).fetchone()


def create(
    conn: sqlite3.Connection,
    *,
    user_id: int,
    name: str,
    role: str,
    department: str,
    manager_id: int | None,
) -> int:
    conn.execute(
        """
        INSERT INTO users (id, name, role, department, manager_id)
        VALUES (?, ?, ?, ?, ?)
        """,
        (user_id, name, role, department, manager_id),
    )
    return user_id


def update(
    conn: sqlite3.Connection,
    user_id: int,
    *,
    name: str,
    role: str,
    department: str,
    manager_id: int | None,
) -> None:
    conn.execute(
        """
        UPDATE users SET name = ?, role = ?, department = ?, manager_id = ?
        WHERE id = ?
        """,
        (name, role, department, manager_id, user_id),
    )


def delete(conn: sqlite3.Connection, user_id: int) -> None:
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
