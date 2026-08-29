"""DB の初期化と初回のサンプルデータ投入。

社内利用の小さなアプリなのでマイグレーションの仕組みは持たず、起動時に
CREATE TABLE IF NOT EXISTS を流すだけにしている。
"""

from __future__ import annotations

import sqlite3

from app.repository import db, users

_SEED_USERS = [
    # id, 名前, ロール, 部門, 上長。manager_id の外部キーを満たすよう上長から並べる
    (5, "伊藤 さやか", "admin", "corporate", None),
    (3, "高橋 みなみ", "manager", "sales", 5),
    (7, "山本 ゆい", "manager", "engineering", 5),
    (4, "田中 りく", "finance", "finance", 5),
    (1, "佐藤 あおい", "employee", "sales", 3),
    (2, "鈴木 けんじ", "employee", "sales", 3),
    (6, "渡辺 たくみ", "employee", "engineering", 7),
]


def seed_users(conn: sqlite3.Connection) -> None:
    for user_id, name, role, department, manager_id in _SEED_USERS:
        users.create(
            conn,
            user_id=user_id,
            name=name,
            role=role,
            department=department,
            manager_id=manager_id,
        )


def ensure_database(path: str | None = None) -> None:
    conn = db.connect(path)
    try:
        db.init_schema(conn)
        if not users.list_all(conn):
            seed_users(conn)
    finally:
        conn.close()
