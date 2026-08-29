"""経費申請の承認と却下。

必要な承認段数は金額で決まる（app.domain.approval_policy）。何段目を誰が承認
できるかの判断はこのモジュールに集める。
"""

from __future__ import annotations

import sqlite3

from app.domain import approval_policy, state_machine
from app.money import Money
from app.repository import audit, db, expenses, users
from app.services import notification

APPROVER_ROLES = ("manager", "finance", "admin")

OPEN_STATUSES = (state_machine.SUBMITTED, state_machine.PARTIALLY_APPROVED)


class ApprovalError(Exception):
    """承認・却下が受け付けられないときに投げる。"""


def amount_of(expense: sqlite3.Row) -> Money:
    return Money(expense["amount_minor"], expense["currency"])


def next_step(conn: sqlite3.Connection, expense_id: int) -> int:
    """次に必要な承認は何段目か。"""
    return len(expenses.approvals_for(conn, expense_id)) + 1


def pending_expenses(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """まだ承認が終わっていない申請を返す。"""
    return expenses.list_by_status(conn, OPEN_STATUSES)


def pending_for(conn: sqlite3.Connection, approver: sqlite3.Row) -> list[sqlite3.Row]:
    """この承認者がいま処理できる申請だけを返す。"""
    return [e for e in pending_expenses(conn) if can_act_on(conn, e, approver)]


def progress(conn: sqlite3.Connection, expense: sqlite3.Row) -> tuple[int, int]:
    """(済んだ段数, 必要な段数) を返す。"""
    done = len(expenses.approvals_for(conn, expense["id"]))
    return done, approval_policy.required_steps(amount_of(expense))


def can_act_on(
    conn: sqlite3.Connection, expense: sqlite3.Row, approver: sqlite3.Row
) -> bool:
    """この承認者がこの申請の次の段を処理できるか。"""
    if expense["status"] not in OPEN_STATUSES:
        return False
    step = next_step(conn, expense["id"])
    if step > approval_policy.required_steps(amount_of(expense)):
        return False
    return approver["role"] == approval_policy.role_for_step(step)


def approve(
    conn: sqlite3.Connection,
    *,
    expense_id: int,
    approver_id: int,
    comment: str = "",
) -> str:
    """申請を1段承認し、承認後の状態を返す。"""
    expense = _load(conn, expense_id)
    if expense["status"] not in OPEN_STATUSES:
        # 終了済みの申請への承認は状態遷移として弾く
        state_machine.transition(expense["status"], state_machine.APPROVED)
    step = next_step(conn, expense_id)
    required = approval_policy.required_steps(amount_of(expense))
    if step > required:
        raise ApprovalError("この申請の承認はすでに完了しています")
    _authorize(conn, approver_id, step)

    next_status = (
        state_machine.APPROVED if step == required else state_machine.PARTIALLY_APPROVED
    )
    return _decide(
        conn,
        expense=expense,
        step=step,
        approver_id=approver_id,
        comment=comment,
        decision="approved",
        next_status=next_status,
    )


def reject(
    conn: sqlite3.Connection,
    *,
    expense_id: int,
    approver_id: int,
    comment: str = "",
) -> str:
    """申請を却下し、却下後の状態を返す。何段目であっても却下は最終。"""
    expense = _load(conn, expense_id)
    if expense["status"] not in OPEN_STATUSES:
        # 終了済みの申請への却下も状態遷移として弾く
        state_machine.transition(expense["status"], state_machine.REJECTED)
    step = next_step(conn, expense_id)
    _authorize(conn, approver_id, step)
    return _decide(
        conn,
        expense=expense,
        step=step,
        approver_id=approver_id,
        comment=comment,
        decision="rejected",
        next_status=state_machine.REJECTED,
    )


def _load(conn: sqlite3.Connection, expense_id: int) -> sqlite3.Row:
    expense = expenses.get(conn, expense_id)
    if expense is None:
        raise ApprovalError("申請が見つかりません")
    return expense


def _authorize(conn: sqlite3.Connection, approver_id: int, step: int) -> None:
    """その段を承認できる立場かを確かめる。

    ルータの require_role は「承認者の集合に属するか」までしか見ない。何段目を
    誰が承認できるかはここで判定する。
    """
    approver = users.get(conn, approver_id)
    if approver is None:
        raise ApprovalError("承認者が見つかりません")
    if approver["role"] != approval_policy.role_for_step(step):
        raise ApprovalError(
            f"{approval_policy.label_for_step(step)}承認は "
            f"{approval_policy.role_for_step(step)} が行います"
        )


def _decide(
    conn: sqlite3.Connection,
    *,
    expense: sqlite3.Row,
    step: int,
    approver_id: int,
    comment: str,
    decision: str,
    next_status: str,
) -> str:
    status = state_machine.transition(expense["status"], next_status)

    with db.transaction(conn):
        expenses.add_approval(
            conn,
            expense_id=expense["id"],
            step=step,
            approver_id=approver_id,
            decision=decision,
            comment=comment,
        )
        expenses.update_status(conn, expense["id"], status)
        audit.record(
            conn,
            entity_type="expense",
            entity_id=expense["id"],
            action=f"{approval_policy.label_for_step(step)} {decision}",
            actor_id=approver_id,
            detail=comment,
        )
        _notify_next(conn, expense, status, step)
    return status


def _notify_next(
    conn: sqlite3.Connection, expense: sqlite3.Row, status: str, step: int
) -> None:
    if status == state_machine.PARTIALLY_APPROVED:
        notification.notify_all_approvers(conn, expense, step=step + 1)
        return
    outcome = "承認されました" if status == state_machine.APPROVED else "却下されました"
    notification.notify_submitter(
        conn, expense["id"], f"申請 #{expense['id']} は{outcome}"
    )
