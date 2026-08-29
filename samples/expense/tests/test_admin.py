from __future__ import annotations

from datetime import date

from app.repository import users

TODAY = date.today().isoformat()


def test_only_admins_reach_user_management(as_user):
    assert as_user(1).get("/admin/users").status_code == 403
    assert as_user(4).get("/admin/users").status_code == 403
    assert as_user(5).get("/admin/users").status_code == 200


def test_adding_a_user(as_user, conn):
    before = len(users.list_all(conn))
    as_user(5).post(
        "/admin/users",
        data={"name": "中村 そう", "role": "employee", "department": "sales", "manager_id": "3"},
    )
    after = users.list_all(conn)
    assert len(after) == before + 1
    assert after[-1]["name"] == "中村 そう"


def test_unknown_roles_are_rejected(as_user):
    response = as_user(5).post(
        "/admin/users",
        data={"name": "x", "role": "superuser", "department": "sales", "manager_id": ""},
        follow_redirects=False,
    )
    assert response.status_code == 400


def test_proxy_submission_creates_an_expense_for_someone_else(as_user, conn):
    from app.repository import expenses

    as_user(5).post(
        "/admin/expenses",
        data={
            "submitter_id": "1",
            "amount": "12,000",
            "category": "transport",
            "description": "紙で回ってきた交通費",
            "incurred_on": TODAY,
        },
    )
    rows = expenses.list_for_submitter(conn, 1)
    assert rows[0]["description"] == "紙で回ってきた交通費"
