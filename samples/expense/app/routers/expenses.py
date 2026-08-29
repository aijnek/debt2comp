"""経費申請の提出と閲覧。"""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

from app import config
from app.deps import ALL_ROLES, get_conn, require_role
from app.money import Money
from app.repository import audit, expenses
from app.services import approval, payment, submission
from app.util import uploads
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
        request, conn, user, "expense_new.html", {"categories": config.CATEGORIES, "receipt_required_above": config.RECEIPT_REQUIRED_ABOVE.format()}
    )


@router.post("/expenses")
async def create_expense(
    request: Request,
    amount: str = Form(...),
    category: str = Form(...),
    description: str = Form(...),
    incurred_on: str = Form(...),
    receipt: UploadFile | None = File(None),
    conn: sqlite3.Connection = Depends(get_conn),
    user=Depends(require_role(*ALL_ROLES)),
):
    try:
        money = Money.parse(amount)
        receipt_name = None
        if receipt is not None and receipt.filename:
            receipt_name = uploads.store_receipt(await receipt.read(), receipt.filename)
        if receipt_name is None and money > config.RECEIPT_REQUIRED_ABOVE:
            raise submission.ValidationError(
                f"{config.RECEIPT_REQUIRED_ABOVE.format()} を超える申請には領収書が要ります"
            )
        expense_id = submission.submit_expense(
            conn,
            submitter_id=user["id"],
            amount=money,
            category=category,
            description=description,
            incurred_on=incurred_on,
            receipt_name=receipt_name,
        )
    except (submission.ValidationError, uploads.UploadError, ValueError) as exc:
        return templating.render(
            request,
            conn,
            user,
            "expense_new.html",
            {"categories": config.CATEGORIES, "receipt_required_above": config.RECEIPT_REQUIRED_ABOVE.format(), "error": str(exc), "form": {
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
            "can_approve": approval.can_act_on(conn, expense, user),
            "progress": approval.progress(conn, expense),
            "can_pay": payment.can_pay(expense, user),
            "payment": expenses.payment_for(conn, expense_id),
            "money": Money,
        },
    )


@router.get("/expenses/{expense_id}/receipt")
def download_receipt(
    expense_id: int,
    conn: sqlite3.Connection = Depends(get_conn),
    user=Depends(require_role(*ALL_ROLES)),
):
    expense = expenses.get(conn, expense_id)
    if expense is None or not expense["receipt_name"]:
        raise HTTPException(status_code=404, detail="領収書がありません")
    path = uploads.receipt_path(expense["receipt_name"])
    if path is None:
        raise HTTPException(status_code=404, detail="領収書の実体が見つかりません")
    return FileResponse(path)
