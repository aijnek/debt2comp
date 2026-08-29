"""自分あての通知の一覧。"""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app import templating
from app.deps import ALL_ROLES, get_conn, require_role
from app.repository import notifications

router = APIRouter()


@router.get("/notifications", response_class=HTMLResponse)
def inbox(
    request: Request,
    conn: sqlite3.Connection = Depends(get_conn),
    user=Depends(require_role(*ALL_ROLES)),
) -> HTMLResponse:
    return templating.render(
        request,
        conn,
        user,
        "notifications.html",
        {"notifications": notifications.list_for_user(conn, user["id"])},
    )


@router.post("/notifications/read")
def mark_read(
    conn: sqlite3.Connection = Depends(get_conn),
    user=Depends(require_role(*ALL_ROLES)),
):
    notifications.mark_all_read(conn, user["id"])
    return RedirectResponse(url="/notifications", status_code=303)
