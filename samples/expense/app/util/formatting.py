"""画面表示のこまごました整形。"""

from __future__ import annotations

from datetime import datetime


def short_datetime(value: str) -> str:
    """ISO8601 の文字列を 'MM/DD HH:MM' にする。読めなければそのまま返す。"""
    try:
        return datetime.fromisoformat(value).strftime("%m/%d %H:%M")
    except ValueError:
        return value


def truncate(text: str, limit: int = 40) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


def role_label(role: str) -> str:
    return {
        "employee": "社員",
        "manager": "上長",
        "finance": "経理",
        "admin": "管理部門",
    }.get(role, role)
