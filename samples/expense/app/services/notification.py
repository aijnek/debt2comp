"""承認待ちの通知。

送信はリクエストの中で同期的に行う。キューを挟まない理由は docs/adr/0002 を参照。
"""

from __future__ import annotations

import sqlite3

from app.domain import approval_policy
from app.money import Money
from app.repository import expenses, notifications, users


def notify_all_approvers(
    conn: sqlite3.Connection, expense: sqlite3.Row, step: int
) -> list[int]:
    """次の段の承認者に、承認待ちがある旨を通知する。

    通知した相手の user id を返す。
    """
    try:
        role = approval_policy.role_for_step(step)
    except ValueError:
        return []

    amount = Money(expense["amount_minor"], expense["currency"])
    message = (
        f"申請 #{expense['id']}（{amount.format()}／{expense['description']}）の"
        f"{approval_policy.label_for_step(step)}承認をお願いします"
    )

    notified: list[int] = []
    for candidate in users.list_by_role(conn, role):
        if candidate["id"] == expense["submitter_id"]:
            continue
        notifications.create(
            conn,
            expense_id=expense["id"],
            recipient_id=candidate["id"],
            message=message,
        )
        notified.append(candidate["id"])
        break
    return notified


def notify_submitter(
    conn: sqlite3.Connection, expense_id: int, message: str
) -> None:
    """申請者に結果を伝える。"""
    expense = expenses.get(conn, expense_id)
    if expense is None:
        return
    notifications.create(
        conn,
        expense_id=expense_id,
        recipient_id=expense["submitter_id"],
        message=message,
    )
