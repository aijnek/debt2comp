from __future__ import annotations

from datetime import date

import pytest

from app.domain import state_machine
from app.money import Money
from app.repository import expenses
from app.services import approval, submission

TODAY = date.today().isoformat()


def submit(conn, submitter_id=1, amount=12000):
    return submission.submit_expense(
        conn,
        submitter_id=submitter_id,
        amount=Money(amount),
        category="transport",
        description="顧客訪問の交通費",
        incurred_on=TODAY,
    )


def test_approval_moves_the_expense_forward(conn):
    expense_id = submit(conn)
    approval.approve(conn, expense_id=expense_id, approver_id=3)
    assert expenses.get(conn, expense_id)["status"] == state_machine.APPROVED


def test_expensive_expenses_need_a_second_approval(conn):
    expense_id = submit(conn, amount=80000)

    approval.approve(conn, expense_id=expense_id, approver_id=3)
    assert expenses.get(conn, expense_id)["status"] == state_machine.PARTIALLY_APPROVED

    approval.approve(conn, expense_id=expense_id, approver_id=4)
    assert expenses.get(conn, expense_id)["status"] == state_machine.APPROVED


def test_the_second_step_needs_the_finance_role(conn, as_user):
    expense_id = submit(conn, amount=80000)
    approval.approve(conn, expense_id=expense_id, approver_id=3)

    response = as_user(7).post(f"/expenses/{expense_id}/approve", data={"comment": ""})
    assert response.status_code == 400
    assert expenses.get(conn, expense_id)["status"] == state_machine.PARTIALLY_APPROVED


def test_rejection_is_terminal(conn):
    expense_id = submit(conn)
    approval.reject(conn, expense_id=expense_id, approver_id=3, comment="領収書なし")
    assert expenses.get(conn, expense_id)["status"] == state_machine.REJECTED
    with pytest.raises(state_machine.TransitionError):
        approval.approve(conn, expense_id=expense_id, approver_id=3)


def test_decision_is_recorded_with_the_approver(conn):
    expense_id = submit(conn)
    approval.approve(conn, expense_id=expense_id, approver_id=3, comment="ok")
    (record,) = expenses.approvals_for(conn, expense_id)
    assert record["approver_id"] == 3
    assert record["decision"] == "approved"
    assert record["comment"] == "ok"


def test_employees_cannot_reach_the_approval_screen(as_user):
    assert as_user(1).get("/approvals").status_code == 403
    assert as_user(3).get("/approvals").status_code == 200


def test_employees_cannot_approve_through_the_endpoint(as_user, conn):
    expense_id = submit(conn)
    response = as_user(2).post(f"/expenses/{expense_id}/approve", data={"comment": ""})
    assert response.status_code == 403
    assert expenses.get(conn, expense_id)["status"] == state_machine.SUBMITTED


def test_a_fully_approved_expense_cannot_be_rejected(conn):
    expense_id = submit(conn, amount=80000)
    approval.approve(conn, expense_id=expense_id, approver_id=3)
    approval.approve(conn, expense_id=expense_id, approver_id=4)
    with pytest.raises(state_machine.TransitionError):
        approval.reject(conn, expense_id=expense_id, approver_id=4)
