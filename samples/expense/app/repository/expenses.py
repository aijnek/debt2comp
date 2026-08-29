"""expenses / approvals / payments テーブルの読み書き。

申請とその承認・支払いは1つのまとまりとして扱うので、同じモジュールに置く。
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

from app.money import Money


def create(
    conn: sqlite3.Connection,
    *,
    submitter_id: int,
    amount: Money,
    category: str,
    description: str,
    incurred_on: str,
    receipt_name: str | None,
    status: str,
) -> int:
    cur = conn.execute(
        """
        INSERT INTO expenses (
            submitter_id, amount_minor, currency, category, description,
            incurred_on, receipt_name, status, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            submitter_id,
            amount.minor,
            amount.currency,
            category,
            description,
            incurred_on,
            receipt_name,
            status,
            datetime.now(UTC).isoformat(timespec="seconds"),
        ),
    )
    return int(cur.lastrowid)


def get(conn: sqlite3.Connection, expense_id: int) -> sqlite3.Row | None:
    return conn.execute(
        """
        SELECT e.*, u.name AS submitter_name, u.department AS submitter_department
        FROM expenses e
        JOIN users u ON u.id = e.submitter_id
        WHERE e.id = ?
        """,
        (expense_id,),
    ).fetchone()


def list_all(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT e.*, u.name AS submitter_name
        FROM expenses e
        JOIN users u ON u.id = e.submitter_id
        ORDER BY e.id DESC
        """
    ).fetchall()


def list_for_submitter(conn: sqlite3.Connection, submitter_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT e.*, u.name AS submitter_name
        FROM expenses e
        JOIN users u ON u.id = e.submitter_id
        WHERE e.submitter_id = ?
        ORDER BY e.id DESC
        """,
        (submitter_id,),
    ).fetchall()


def list_by_status(conn: sqlite3.Connection, statuses: tuple[str, ...]) -> list[sqlite3.Row]:
    placeholders = ", ".join("?" for _ in statuses)
    return conn.execute(
        f"""
        SELECT e.*, u.name AS submitter_name
        FROM expenses e
        JOIN users u ON u.id = e.submitter_id
        WHERE e.status IN ({placeholders})
        ORDER BY e.id
        """,
        statuses,
    ).fetchall()


def update_status(conn: sqlite3.Connection, expense_id: int, status: str) -> None:
    """status を書き換える唯一の関数。

    渡す値は app.domain.state_machine.transition() の戻り値であること。ここでは
    遷移の妥当性を検査しない（ドメインの判断を SQL の層に持ち込まないため）。
    """
    conn.execute("UPDATE expenses SET status = ? WHERE id = ?", (status, expense_id))


def add_approval(
    conn: sqlite3.Connection,
    *,
    expense_id: int,
    step: int,
    approver_id: int,
    decision: str,
    comment: str = "",
) -> None:
    conn.execute(
        """
        INSERT INTO approvals (expense_id, step, approver_id, decision, comment, decided_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            expense_id,
            step,
            approver_id,
            decision,
            comment,
            datetime.now(UTC).isoformat(timespec="seconds"),
        ),
    )


def approvals_for(conn: sqlite3.Connection, expense_id: int) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT a.*, u.name AS approver_name
        FROM approvals a
        JOIN users u ON u.id = a.approver_id
        WHERE a.expense_id = ?
        ORDER BY a.step
        """,
        (expense_id,),
    ).fetchall()


def record_payment(
    conn: sqlite3.Connection,
    *,
    expense_id: int,
    paid_by: int,
    reference: str,
) -> None:
    conn.execute(
        """
        INSERT INTO payments (expense_id, paid_by, reference, paid_at)
        VALUES (?, ?, ?, ?)
        """,
        (
            expense_id,
            paid_by,
            reference,
            datetime.now(UTC).isoformat(timespec="seconds"),
        ),
    )


def payment_for(conn: sqlite3.Connection, expense_id: int) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT * FROM payments WHERE expense_id = ?", (expense_id,)
    ).fetchone()
