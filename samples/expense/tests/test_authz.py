"""承認できる立場かどうかの判定。

「誰が承認できるか」はルータの require_role では決まりきらない。段ごとの判定は
services/approval.py の _authorize に集約されているので、ここで確かめる。
"""

from __future__ import annotations

from datetime import date

import pytest

from app.money import Money
from app.repository import expenses, users
from app.services import approval, submission

TODAY = date.today().isoformat()


def submit(conn, submitter_id, amount=12000):
    return submission.submit_expense(
        conn,
        submitter_id=submitter_id,
        amount=Money(amount),
        category="transport",
        description="顧客訪問の交通費",
        incurred_on=TODAY,
    )


def test_self_approval_is_rejected(conn):
    # 高橋（manager）が自分で出した申請を、自分で承認できてはいけない
    expense_id = submit(conn, submitter_id=3)
    with pytest.raises(approval.ApprovalError):
        approval.approve(conn, expense_id=expense_id, approver_id=3)


def test_the_first_step_needs_the_submitters_own_manager(conn):
    expense_id = submit(conn, submitter_id=1)
    # 山本は manager だが、佐藤の上長ではない
    with pytest.raises(approval.ApprovalError):
        approval.approve(conn, expense_id=expense_id, approver_id=7)
    approval.approve(conn, expense_id=expense_id, approver_id=3)
    assert expenses.approvals_for(conn, expense_id)[0]["approver_id"] == 3


def test_a_managers_expense_goes_to_their_own_manager(conn):
    expense_id = submit(conn, submitter_id=3)
    approval.approve(conn, expense_id=expense_id, approver_id=5)
    assert expenses.approvals_for(conn, expense_id)[0]["approver_id"] == 5


def test_a_later_step_approver_cannot_be_the_submitter(conn):
    # 田中（finance）自身の高額申請は、二次を自分で通せない
    expense_id = submit(conn, submitter_id=4, amount=80000)
    approval.approve(conn, expense_id=expense_id, approver_id=5)
    with pytest.raises(approval.ApprovalError):
        approval.approve(conn, expense_id=expense_id, approver_id=4)


def test_the_screen_and_the_endpoint_agree(conn):
    expense_id = submit(conn, submitter_id=1)
    expense = expenses.get(conn, expense_id)

    assert approval.can_act_on(conn, expense, users.get(conn, 3))
    assert not approval.can_act_on(conn, expense, users.get(conn, 7))
    assert not approval.can_act_on(conn, expense, users.get(conn, 1))
