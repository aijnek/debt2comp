"""承認待ちの一覧と、承認・却下の実行。"""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app import templating
from app.deps import get_conn, require_role
from app.money import Money
from app.services import approval

router = APIRouter()


@router.get("/approvals", response_class=HTMLResponse)
def pending(
    request: Request,
    conn: sqlite3.Connection = Depends(get_conn),
    user=Depends(require_role(*approval.APPROVER_ROLES)),
) -> HTMLResponse:
    return templating.render(
        request,
        conn,
        user,
        "approvals.html",
        {"expenses": approval.pending_for(conn, user), "money": Money},
    )


@router.post("/expenses/{expense_id}/approve")
def approve(
    expense_id: int,
    comment: str = Form(""),
    conn: sqlite3.Connection = Depends(get_conn),
    user=Depends(require_role(*approval.APPROVER_ROLES)),
):
    try:
        approval.approve(
            conn, expense_id=expense_id, approver_id=user["id"], comment=comment
        )
    except approval.ApprovalError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RedirectResponse(url=f"/expenses/{expense_id}", status_code=303)


@router.post("/expenses/{expense_id}/reject")
def reject(
    expense_id: int,
    comment: str = Form(""),
    conn: sqlite3.Connection = Depends(get_conn),
    user=Depends(require_role(*approval.APPROVER_ROLES)),
):
    try:
        approval.reject(
            conn, expense_id=expense_id, approver_id=user["id"], comment=comment
        )
    except approval.ApprovalError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RedirectResponse(url=f"/expenses/{expense_id}", status_code=303)
