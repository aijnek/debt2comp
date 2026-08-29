"""管理部門向けのユーザー管理と代理申請。"""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app import templating
from app.deps import get_conn, require_role
from app.money import Money
from app.repository import users
from app.services import submission
from app.util import formatting

router = APIRouter(prefix="/admin")


@router.get("/users", response_class=HTMLResponse)
def user_list(
    request: Request,
    conn: sqlite3.Connection = Depends(get_conn),
    user=Depends(require_role("admin")),
) -> HTMLResponse:
    return templating.render(
        request,
        conn,
        user,
        "admin_users.html",
        {"users": users.list_all(conn), "roles": users.ROLES, "fmt": formatting},
    )


@router.post("/users")
def create_user(
    name: str = Form(...),
    role: str = Form(...),
    department: str = Form(...),
    manager_id: str = Form(""),
    conn: sqlite3.Connection = Depends(get_conn),
    user=Depends(require_role("admin")),
):
    if role not in users.ROLES:
        raise HTTPException(status_code=400, detail="未知のロールです")
    users.create(
        conn,
        user_id=users.next_id(conn),
        name=name,
        role=role,
        department=department,
        manager_id=int(manager_id) if manager_id.isdigit() else None,
    )
    return RedirectResponse(url="/admin/users", status_code=303)


@router.post("/users/{user_id}")
def update_user(
    user_id: int,
    name: str = Form(...),
    role: str = Form(...),
    department: str = Form(...),
    manager_id: str = Form(""),
    conn: sqlite3.Connection = Depends(get_conn),
    user=Depends(require_role("admin")),
):
    if role not in users.ROLES:
        raise HTTPException(status_code=400, detail="未知のロールです")
    users.update(
        conn,
        user_id,
        name=name,
        role=role,
        department=department,
        manager_id=int(manager_id) if manager_id.isdigit() else None,
    )
    return RedirectResponse(url="/admin/users", status_code=303)


@router.post("/users/{user_id}/delete")
def delete_user(
    user_id: int,
    conn: sqlite3.Connection = Depends(get_conn),
    user=Depends(require_role("admin")),
):
    users.delete(conn, user_id)
    return RedirectResponse(url="/admin/users", status_code=303)


@router.post("/expenses")
def proxy_submit(
    submitter_id: int = Form(...),
    amount: str = Form(...),
    category: str = Form(...),
    description: str = Form(...),
    incurred_on: str = Form(...),
    conn: sqlite3.Connection = Depends(get_conn),
    user=Depends(require_role("admin")),
):
    """紙で回ってきた申請を管理部門が代理で入力する。

    領収書の原本は経理が紙で保管しているので、ここでは添付を取らない。
    """
    try:
        expense_id = submission.submit_expense(
            conn,
            submitter_id=submitter_id,
            amount=Money.parse(amount),
            category=category,
            description=description,
            incurred_on=incurred_on,
        )
    except (submission.ValidationError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RedirectResponse(url=f"/expenses/{expense_id}", status_code=303)
