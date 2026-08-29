"""操作するユーザーの切り替え。

社内SSOを入れるまでの仮置き。誰として振る舞うかを cookie に持つ。
"""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Form
from fastapi.responses import RedirectResponse

from app.deps import ALL_ROLES, SESSION_COOKIE, get_conn, require_role
from app.repository import users

router = APIRouter()


@router.post("/session/user")
def switch_user(
    user_id: int = Form(...),
    conn: sqlite3.Connection = Depends(get_conn),
    _actor=Depends(require_role(*ALL_ROLES)),
) -> RedirectResponse:
    target = users.get(conn, user_id)
    response = RedirectResponse(url="/", status_code=303)
    if target is not None:
        response.set_cookie(SESSION_COOKIE, str(user_id), httponly=True, samesite="lax")
    return response
