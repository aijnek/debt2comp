"""申請の状態遷移。

status を書き換えたい箇所は必ずこの transition() を通す。許される遷移の一覧が
1箇所にまとまっていないと、ルータやサービスが増えるたびに「この状態からこれに
飛べたか」の判断が散らばるため。
"""

from __future__ import annotations

SUBMITTED = "submitted"
PARTIALLY_APPROVED = "partially_approved"
APPROVED = "approved"
REJECTED = "rejected"
PAID = "paid"

STATUSES = (SUBMITTED, PARTIALLY_APPROVED, APPROVED, REJECTED, PAID)

_ALLOWED: dict[str, frozenset[str]] = {
    SUBMITTED: frozenset({PARTIALLY_APPROVED, APPROVED, REJECTED}),
    PARTIALLY_APPROVED: frozenset({APPROVED, REJECTED}),
    APPROVED: frozenset({PAID}),
    REJECTED: frozenset(),
    PAID: frozenset(),
}


class TransitionError(Exception):
    """許されていない状態遷移を要求されたときに投げる。"""


def transition(current: str, to: str) -> str:
    """current から to への遷移が許されていれば to を返す。

    戻り値をそのまま永続化に渡すことで、遷移の検査を迂回した status の書き込みを
    レビューで見つけやすくしている。
    """
    if current not in _ALLOWED:
        raise TransitionError(f"未知の状態です: {current}")
    if to not in STATUSES:
        raise TransitionError(f"未知の状態です: {to}")
    if to not in _ALLOWED[current]:
        raise TransitionError(f"{current} から {to} へは遷移できません")
    return to


def is_terminal(status: str) -> bool:
    return not _ALLOWED.get(status, frozenset())
