"""支払い待ちの一覧と、支払いの実行。"""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app import templating
from app.deps import get_conn, require_role
from app.money import Money
from app.services import payment

router = APIRouter()


@router.get("/payments", response_class=HTMLResponse)
def payable(
    request: Request,
    conn: sqlite3.Connection = Depends(get_conn),
    user=Depends(require_role(*payment.PAYER_ROLES)),
) -> HTMLResponse:
    return templating.render(
        request,
        conn,
        user,
        "payments.html",
        {"expenses": payment.payable_expenses(conn), "money": Money},
    )


@router.post("/expenses/{expense_id}/pay")
def pay(
    expense_id: int,
    reference: str = Form(...),
    conn: sqlite3.Connection = Depends(get_conn),
    user=Depends(require_role(*payment.PAYER_ROLES)),
):
    try:
        payment.pay(
            conn, expense_id=expense_id, actor_id=user["id"], reference=reference
        )
    except payment.PaymentError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RedirectResponse(url=f"/expenses/{expense_id}", status_code=303)
