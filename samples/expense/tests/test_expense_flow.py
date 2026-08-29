from __future__ import annotations

from datetime import date

import pytest

from app.domain import state_machine
from app.money import Money
from app.repository import audit, expenses
from app.services import submission

TODAY = date.today().isoformat()


def submit(conn, submitter_id=1, amount=12000, incurred_on=TODAY):
    return submission.submit_expense(
        conn,
        submitter_id=submitter_id,
        amount=Money(amount),
        category="transport",
        description="顧客訪問の交通費",
        incurred_on=incurred_on,
    )


def test_submitted_expense_starts_in_submitted_state(conn):
    expense_id = submit(conn)
    row = expenses.get(conn, expense_id)
    assert row["status"] == state_machine.SUBMITTED
    assert row["amount_minor"] == 12000


def test_submission_is_recorded_in_the_audit_log(conn):
    expense_id = submit(conn)
    entries = audit.list_for(conn, "expense", expense_id)
    assert [e["action"] for e in entries] == ["submitted"]


def test_amount_over_the_ceiling_is_rejected(conn):
    with pytest.raises(submission.ValidationError):
        submit(conn, amount=1_500_000)


def test_future_and_stale_dates_are_rejected(conn):
    with pytest.raises(submission.ValidationError):
        submit(conn, incurred_on="2999-01-01")
    with pytest.raises(submission.ValidationError):
        submit(conn, incurred_on="2000-01-01")


def test_index_lists_only_your_own_expenses(as_user, conn):
    submit(conn, submitter_id=1)
    submit(conn, submitter_id=2)

    body = as_user(1).get("/").text
    assert body.count("顧客訪問の交通費") == 1


def test_creating_an_expense_through_the_form(as_user):
    response = as_user(1).post(
        "/expenses",
        data={
            "amount": "3,200",
            "category": "meals",
            "description": "会議の弁当",
            "incurred_on": TODAY,
        },
    )
    assert response.status_code == 200
    assert "3,200 JPY" in response.text


def test_invalid_amount_returns_the_form_with_an_error(as_user):
    response = as_user(1).post(
        "/expenses",
        data={
            "amount": "abc",
            "category": "meals",
            "description": "会議の弁当",
            "incurred_on": TODAY,
        },
        follow_redirects=False,
    )
    assert response.status_code == 400
