"""FastAPI の依存性。

認可の判定はここの require_role() に集約する。ルータ側で role を直接見に行くと
判定が散らばり、ルートを足したときの付け忘れが構造的に検出できなくなるため。

DB 接続の生成もここが唯一の入口。db.connect() を呼ぶのはこのモジュールだけで、
以降は依存性として各層に配られる。SQL は repository の中にしか無い。
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable, Iterator

from fastapi import Depends, HTTPException, Request

from app.repository import db, users

ALL_ROLES = ("employee", "manager", "finance", "admin")

# 認証は社内SSOの手前で止めてある。誰として操作するかは cookie で切り替える。
SESSION_COOKIE = "uid"
DEFAULT_USER_ID = 1


def get_conn() -> Iterator[sqlite3.Connection]:
    conn = db.connect()
    try:
        yield conn
    finally:
        conn.close()


def current_user(
    request: Request, conn: sqlite3.Connection = Depends(get_conn)
) -> sqlite3.Row:
    raw = request.cookies.get(SESSION_COOKIE)
    user_id = int(raw) if raw and raw.isdigit() else DEFAULT_USER_ID
    user = users.get(conn, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="不明なユーザーです")
    return user


def require_role(*roles: str) -> Callable[..., sqlite3.Row]:
    """指定したロールのいずれかを持つ場合だけ通す依存性を作る。

    すべての公開ルートはこの依存性を経由する。tools/audit_routes.py がそれを
    機械的に検査している。
    """
    for role in roles:
        if role not in ALL_ROLES:
            raise ValueError(f"未知のロール: {role}")

    def role_guard(user: sqlite3.Row = Depends(current_user)) -> sqlite3.Row:
        if user["role"] not in roles:
            raise HTTPException(
                status_code=403,
                detail=f"この操作には {'/'.join(roles)} のいずれかが必要です",
            )
        return user

    role_guard.__is_role_guard__ = True
    return role_guard
