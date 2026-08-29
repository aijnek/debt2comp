"""経費申請の提出。"""

from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from app import config
from app.domain import state_machine
from app.money import Money
from app.repository import audit, db, expenses


class ValidationError(Exception):
    """申請内容が受付ルールに反しているときに投げる。"""


def validate_expense(
    amount: Money,
    category: str,
    incurred_on: str,
    today: date | None = None,
) -> None:
    """申請内容を受付ルールに照らす。問題があれば ValidationError を投げる。"""
    if amount.minor <= 0:
        raise ValidationError("金額は 1 以上で入力してください")
    if amount > config.MAX_EXPENSE:
        raise ValidationError(
            f"{config.MAX_EXPENSE.format()} を超える経費は購買申請に回してください"
        )
    if category not in config.CATEGORIES:
        raise ValidationError(f"未知の費目です: {category}")

    try:
        incurred = date.fromisoformat(incurred_on)
    except ValueError:
        raise ValidationError("発生日は YYYY-MM-DD で入力してください") from None

    today = today or date.today()
    if incurred > today:
        raise ValidationError("未来の日付は申請できません")
    if incurred < today - timedelta(days=config.MAX_BACKDATE_DAYS):
        raise ValidationError(
            f"発生日から {config.MAX_BACKDATE_DAYS} 日を過ぎた経費は申請できません"
        )


def submit_expense(
    conn: sqlite3.Connection,
    *,
    submitter_id: int,
    amount: Money,
    category: str,
    description: str,
    incurred_on: str,
    receipt_name: str | None = None,
) -> int:
    """申請を1件受け付け、その id を返す。"""
    validate_expense(amount, category, incurred_on)

    if not description.strip():
        raise ValidationError("用途を入力してください")

    with db.transaction(conn):
        expense_id = expenses.create(
            conn,
            submitter_id=submitter_id,
            amount=amount,
            category=category,
            description=description.strip(),
            incurred_on=incurred_on,
            receipt_name=receipt_name,
            status=state_machine.SUBMITTED,
        )
        audit.record(
            conn,
            entity_type="expense",
            entity_id=expense_id,
            action="submitted",
            actor_id=submitter_id,
            detail=amount.format(),
        )
    return expense_id
