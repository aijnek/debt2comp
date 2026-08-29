from __future__ import annotations

from datetime import date

import pytest

from app.domain import state_machine
from app.money import Money
from app.repository import expenses
from app.services import approval, payment, submission

TODAY = date.today().isoformat()


def approved_expense(conn, amount=12000):
    expense_id = submission.submit_expense(
        conn,
        submitter_id=1,
        amount=Money(amount),
        category="transport",
        description="顧客訪問の交通費",
        incurred_on=TODAY,
    )
    approval.approve(conn, expense_id=expense_id, approver_id=3)
    return expense_id


def test_paying_an_approved_expense(conn):
    expense_id = approved_expense(conn)
    payment.pay(conn, expense_id=expense_id, actor_id=4, reference="FT-001")
    assert expenses.get(conn, expense_id)["status"] == state_machine.PAID
    assert expenses.payment_for(conn, expense_id)["reference"] == "FT-001"


def test_unapproved_expenses_cannot_be_paid(conn):
    expense_id = submission.submit_expense(
        conn,
        submitter_id=1,
        amount=Money(500),
        category="meals",
        description="打ち合わせのコーヒー",
        incurred_on=TODAY,
    )
    with pytest.raises(state_machine.TransitionError):
        payment.pay(conn, expense_id=expense_id, actor_id=4, reference="FT-002")


def test_an_expense_cannot_be_paid_twice(conn):
    expense_id = approved_expense(conn)
    payment.pay(conn, expense_id=expense_id, actor_id=4, reference="FT-003")
    with pytest.raises(state_machine.TransitionError):
        payment.pay(conn, expense_id=expense_id, actor_id=4, reference="FT-004")


def test_reference_is_required(conn):
    expense_id = approved_expense(conn)
    with pytest.raises(payment.PaymentError):
        payment.pay(conn, expense_id=expense_id, actor_id=4, reference="   ")


def test_managers_cannot_reach_the_payment_screen(as_user):
    assert as_user(3).get("/payments").status_code == 403
    assert as_user(4).get("/payments").status_code == 200
