from __future__ import annotations

from datetime import date

from app.money import Money
from app.repository import notifications
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


def test_submitting_notifies_a_manager(conn):
    expense_id = submit(conn)
    inbox = notifications.list_for_user(conn, 3)
    assert len(inbox) == 1
    assert str(expense_id) in inbox[0]["message"]


def test_the_submitter_hears_the_outcome(conn):
    expense_id = submit(conn)
    approval.approve(conn, expense_id=expense_id, approver_id=3)
    inbox = notifications.list_for_user(conn, 1)
    assert inbox[0]["message"].endswith("承認されました")


def test_the_second_step_approver_is_notified(conn):
    expense_id = submit(conn, amount=80000)
    approval.approve(conn, expense_id=expense_id, approver_id=3)
    inbox = notifications.list_for_user(conn, 4)
    assert len(inbox) == 1
    assert "二次" in inbox[0]["message"]


def test_unread_count_drops_after_reading(as_user, conn):
    submit(conn)
    assert notifications.unread_count(conn, 3) == 1
    as_user(3).post("/notifications/read")
    assert notifications.unread_count(conn, 3) == 0
