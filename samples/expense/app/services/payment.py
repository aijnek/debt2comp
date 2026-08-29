"""承認済み申請の支払い実行。"""

from __future__ import annotations

import sqlite3

from app.domain import state_machine
from app.repository import audit, db, expenses

PAYER_ROLES = ("finance", "admin")


class PaymentError(Exception):
    """支払いを受け付けられないときに投げる。"""


def payable_expenses(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return expenses.list_by_status(conn, (state_machine.APPROVED,))


def can_pay(expense: sqlite3.Row, actor: sqlite3.Row) -> bool:
    return (
        actor["role"] in PAYER_ROLES
        and expense["status"] == state_machine.APPROVED
    )


def pay(
    conn: sqlite3.Connection,
    *,
    expense_id: int,
    actor_id: int,
    reference: str,
) -> str:
    """支払いを記録し、支払い後の状態を返す。"""
    expense = expenses.get(conn, expense_id)
    if expense is None:
        raise PaymentError("申請が見つかりません")
    if not reference.strip():
        raise PaymentError("振込参照番号を入力してください")

    status = state_machine.transition(expense["status"], state_machine.PAID)

    with db.transaction(conn):
        expenses.record_payment(
            conn,
            expense_id=expense_id,
            paid_by=actor_id,
            reference=reference.strip(),
        )
        expenses.update_status(conn, expense_id, status)
        audit.record(
            conn,
            entity_type="expense",
            entity_id=expense_id,
            action="paid",
            actor_id=actor_id,
            detail=reference.strip(),
        )
    return status
