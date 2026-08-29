"""経費申請の承認と却下。"""

from __future__ import annotations

import sqlite3

from app.domain import state_machine
from app.repository import audit, db, expenses

APPROVER_ROLES = ("manager", "finance", "admin")


class ApprovalError(Exception):
    """承認・却下が受け付けられないときに投げる。"""


def pending_expenses(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """承認待ちの申請を返す。"""
    return expenses.list_by_status(conn, (state_machine.SUBMITTED,))


def can_act_on(expense: sqlite3.Row, approver: sqlite3.Row) -> bool:
    """この承認者がこの申請を処理できるか。"""
    if approver["role"] not in APPROVER_ROLES:
        return False
    return expense["status"] == state_machine.SUBMITTED


def approve(
    conn: sqlite3.Connection,
    *,
    expense_id: int,
    approver_id: int,
    comment: str = "",
) -> str:
    """申請を承認し、承認後の状態を返す。"""
    return _decide(
        conn,
        expense_id=expense_id,
        approver_id=approver_id,
        comment=comment,
        decision="approved",
        next_status=state_machine.APPROVED,
    )


def reject(
    conn: sqlite3.Connection,
    *,
    expense_id: int,
    approver_id: int,
    comment: str = "",
) -> str:
    """申請を却下し、却下後の状態を返す。"""
    return _decide(
        conn,
        expense_id=expense_id,
        approver_id=approver_id,
        comment=comment,
        decision="rejected",
        next_status=state_machine.REJECTED,
    )


def _decide(
    conn: sqlite3.Connection,
    *,
    expense_id: int,
    approver_id: int,
    comment: str,
    decision: str,
    next_status: str,
) -> str:
    expense = expenses.get(conn, expense_id)
    if expense is None:
        raise ApprovalError("申請が見つかりません")

    status = state_machine.transition(expense["status"], next_status)

    with db.transaction(conn):
        expenses.add_approval(
            conn,
            expense_id=expense_id,
            step=1,
            approver_id=approver_id,
            decision=decision,
            comment=comment,
        )
        expenses.update_status(conn, expense_id, status)
        audit.record(
            conn,
            entity_type="expense",
            entity_id=expense_id,
            action=decision,
            actor_id=approver_id,
            detail=comment,
        )
    return status
