#!/usr/bin/env bash
# 部門別の月次集計モジュールを新しく足す（認可はきちんと通す）。
set -euo pipefail
cd "$(dirname "$0")/../.."

target="samples/expense/app/main.py"
grep -q "app.include_router(admin.router)" "$target" || {
  echo "main.py の形が変わっている。シナリオを更新すること" >&2; exit 2; }

cat > samples/expense/app/repository/reporting.py <<'PY'
"""月次集計のための読み取り。"""

from __future__ import annotations

import sqlite3


def monthly_totals(conn: sqlite3.Connection, month: str) -> list[sqlite3.Row]:
    """指定月に支払われた申請を部門ごとに合計する。month は 'YYYY-MM'。"""
    return conn.execute(
        """
        SELECT u.department AS department,
               COUNT(*) AS count,
               SUM(e.amount_minor) AS total_minor,
               e.currency AS currency
        FROM payments p
        JOIN expenses e ON e.id = p.expense_id
        JOIN users u ON u.id = e.submitter_id
        WHERE substr(p.paid_at, 1, 7) = ?
        GROUP BY u.department, e.currency
        ORDER BY total_minor DESC
        """,
        (month,),
    ).fetchall()
PY

cat > samples/expense/app/services/reporting.py <<'PY'
"""月次の支払い集計。

締めの報告に使う数字なので、支払い済み（paid）だけを数える。承認済みで未払いの
ものを混ぜると、経理の帳簿と合わない数字が出る。
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from app.money import Money
from app.repository import reporting


@dataclass(frozen=True)
class DepartmentTotal:
    department: str
    count: int
    total: Money


def monthly_report(conn: sqlite3.Connection, month: str) -> list[DepartmentTotal]:
    return [
        DepartmentTotal(
            department=row["department"],
            count=int(row["count"]),
            total=Money(int(row["total_minor"]), row["currency"]),
        )
        for row in reporting.monthly_totals(conn, month)
    ]


def grand_total(rows: list[DepartmentTotal]) -> Money:
    if not rows:
        return Money(0)
    total = Money(0, rows[0].total.currency)
    for row in rows:
        total = total + row.total
    return total
PY

cat > samples/expense/app/routers/reports.py <<'PY'
"""月次集計の閲覧。"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from app import templating
from app.deps import get_conn, require_role
from app.services import reporting

router = APIRouter()


@router.get("/reports/monthly", response_class=HTMLResponse)
def monthly(
    request: Request,
    month: str = "",
    conn: sqlite3.Connection = Depends(get_conn),
    user=Depends(require_role("finance", "admin")),
) -> HTMLResponse:
    target = month or datetime.now(UTC).strftime("%Y-%m")
    rows = reporting.monthly_report(conn, target)
    return templating.render(
        request,
        conn,
        user,
        "report_monthly.html",
        {"month": target, "rows": rows, "grand_total": reporting.grand_total(rows)},
    )
PY

cat > samples/expense/app/templates/report_monthly.html <<'PY'
{% extends "base.html" %}
{% block title %}月次集計{% endblock %}
{% block content %}
<h1>月次集計 {{ month }}</h1>
{% if rows %}
<table>
  <thead><tr><th>部門</th><th class="num">件数</th><th class="num">支払額</th></tr></thead>
  <tbody>
    {% for r in rows %}
    <tr><td>{{ r.department }}</td><td class="num">{{ r.count }}</td><td class="num">{{ r.total.format() }}</td></tr>
    {% endfor %}
  </tbody>
  <tfoot><tr><td>合計</td><td class="num">—</td><td class="num">{{ grand_total.format() }}</td></tr></tfoot>
</table>
{% else %}
<p class="empty">この月に支払われた申請はありません。</p>
{% endif %}
{% endblock %}
PY

cat > samples/expense/tests/test_reporting.py <<'PY'
from __future__ import annotations

from datetime import UTC, date, datetime

from app.money import Money
from app.services import approval, payment, reporting, submission

TODAY = date.today().isoformat()
THIS_MONTH = datetime.now(UTC).strftime("%Y-%m")


def paid_expense(conn, submitter_id, amount):
    expense_id = submission.submit_expense(
        conn,
        submitter_id=submitter_id,
        amount=Money(amount),
        category="transport",
        description="集計用",
        incurred_on=TODAY,
    )
    approval.approve(conn, expense_id=expense_id, approver_id=3 if submitter_id in (1, 2) else 7)
    payment.pay(conn, expense_id=expense_id, actor_id=4, reference=f"FT-{expense_id}")
    return expense_id


def test_totals_are_grouped_by_department(conn):
    paid_expense(conn, 1, 1000)
    paid_expense(conn, 2, 2000)
    paid_expense(conn, 6, 500)

    rows = reporting.monthly_report(conn, THIS_MONTH)
    by_department = {r.department: r for r in rows}
    assert by_department["sales"].count == 2
    assert by_department["sales"].total == Money(3000)
    assert by_department["engineering"].total == Money(500)


def test_unpaid_expenses_are_not_counted(conn):
    submission.submit_expense(
        conn,
        submitter_id=1,
        amount=Money(9000),
        category="transport",
        description="未払い",
        incurred_on=TODAY,
    )
    assert reporting.monthly_report(conn, THIS_MONTH) == []


def test_grand_total_sums_every_department(conn):
    paid_expense(conn, 1, 1000)
    paid_expense(conn, 6, 500)
    rows = reporting.monthly_report(conn, THIS_MONTH)
    assert reporting.grand_total(rows) == Money(1500)
PY

python3 - <<'PY'
import pathlib
p = pathlib.Path("samples/expense/app/main.py")
s = p.read_text()
s = s.replace("from app.routers import admin, approvals, expenses, notifications, payments, session",
              "from app.routers import (\n    admin,\n    approvals,\n    expenses,\n    notifications,\n    payments,\n    reports,\n    session,\n)")
s = s.replace("app.include_router(admin.router)",
              "app.include_router(admin.router)\napp.include_router(reports.router)")
p.write_text(s)

p = pathlib.Path("samples/expense/app/templates/base.html")
s = p.read_text()
s = s.replace('      <a href="/payments">支払い待ち</a>',
              '      <a href="/payments">支払い待ち</a>\n      <a href="/reports/monthly">月次集計</a>')
p.write_text(s)
PY

echo "適用した: 月次集計モジュール（repository / services / routers / template / tests）を追加"
