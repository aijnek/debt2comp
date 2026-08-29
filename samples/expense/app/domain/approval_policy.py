"""必要な承認段数を金額から決める。

3万円を超える申請は2段階（一次: 申請者の上長、二次: 経理）の承認を必要とする。
それ以下は上長の承認だけで通す。段数を金額だけで決めるのは、部門ごとの例外を
持ち込むと申請者から見て何段必要かが予測できなくなるため。
"""

from __future__ import annotations

from app import config
from app.money import Money

# 段目 -> その段を承認するロール
STEP_ROLES: dict[int, str] = {
    1: "manager",
    2: "finance",
}

STEP_LABELS: dict[int, str] = {
    1: "一次（上長）",
    2: "二次（経理）",
}


def required_steps(amount: Money) -> int:
    """この金額の申請に必要な承認段数を返す。"""
    if amount > config.TWO_STEP_THRESHOLD:
        return 2
    return 1


def role_for_step(step: int) -> str:
    """指定の段を承認できるロールを返す。"""
    if step not in STEP_ROLES:
        raise ValueError(f"存在しない承認段です: {step}")
    return STEP_ROLES[step]


def label_for_step(step: int) -> str:
    return STEP_LABELS.get(step, f"{step}段目")
