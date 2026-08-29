"""経費申請の提出と閲覧。"""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app import config
from app.deps import ALL_ROLES, get_conn, require_role
from app.money import Money
from app.repository import audit, expenses
from app.services import approval, payment, submission
from app import templating

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def index(
    request: Request,
    conn: sqlite3.Connection = Depends(get_conn),
    user=Depends(require_role(*ALL_ROLES)),
) -> HTMLResponse:
    rows = expenses.list_for_submitter(conn, user["id"])
    return templating.render(
        request, conn, user, "index.html", {"expenses": rows, "money": Money}
    )


@router.get("/expenses/new", response_class=HTMLResponse)
def new_expense_form(
    request: Request,
    conn: sqlite3.Connection = Depends(get_conn),
    user=Depends(require_role(*ALL_ROLES)),
) -> HTMLResponse:
    return templating.render(
        request, conn, user, "expense_new.html", {"categories": config.CATEGORIES}
    )


@router.post("/expenses")
def create_expense(
    request: Request,
    amount: str = Form(...),
    category: str = Form(...),
    description: str = Form(...),
    incurred_on: str = Form(...),
    conn: sqlite3.Connection = Depends(get_conn),
    user=Depends(require_role(*ALL_ROLES)),
):
    try:
        money = Money.parse(amount)
        expense_id = submission.submit_expense(
            conn,
            submitter_id=user["id"],
            amount=money,
            category=category,
            description=description,
            incurred_on=incurred_on,
        )
    except (submission.ValidationError, ValueError) as exc:
        return templating.render(
            request,
            conn,
            user,
            "expense_new.html",
            {"categories": config.CATEGORIES, "error": str(exc), "form": {
                "amount": amount,
                "category": category,
                "description": description,
                "incurred_on": incurred_on,
            }},
            status_code=400,
        )
    return RedirectResponse(url=f"/expenses/{expense_id}", status_code=303)


@router.get("/expenses/{expense_id}", response_class=HTMLResponse)
def expense_detail(
    request: Request,
    expense_id: int,
    conn: sqlite3.Connection = Depends(get_conn),
    user=Depends(require_role(*ALL_ROLES)),
) -> HTMLResponse:
    expense = expenses.get(conn, expense_id)
    if expense is None:
        raise HTTPException(status_code=404, detail="申請が見つかりません")
    return templating.render(
        request,
        conn,
        user,
        "expense_detail.html",
        {
            "expense": expense,
            "approvals": expenses.approvals_for(conn, expense_id),
            "history": audit.list_for(conn, "expense", expense_id),
            "can_approve": approval.can_act_on(expense, user),
            "can_pay": payment.can_pay(expense, user),
            "payment": expenses.payment_for(conn, expense_id),
            "money": Money,
        },
    )
