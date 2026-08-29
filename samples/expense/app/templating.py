"""テンプレートの共通配線。

全画面のヘッダにユーザー切り替えを出すので、そのためのデータをここで足す。
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.repository import users

_env = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


def render(
    request: Request,
    conn: sqlite3.Connection,
    user: sqlite3.Row,
    name: str,
    context: dict[str, Any] | None = None,
    status_code: int = 200,
) -> HTMLResponse:
    merged: dict[str, Any] = {
        "current_user": user,
        "all_users": users.list_all(conn),
    }
    merged.update(context or {})
    return _env.TemplateResponse(request, name, merged, status_code=status_code)
