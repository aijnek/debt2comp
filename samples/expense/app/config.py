"""申請の受付ルール。

金額のしきい値や上限はコードに置き、DB に持たない。理由は docs/adr/0001 を参照。
"""

from app.money import Money

# これを超える金額は経費精算では受け付けず、購買申請に回してもらう
MAX_EXPENSE = Money(1_000_000)

# これを超える申請には領収書の添付が要る
RECEIPT_REQUIRED_ABOVE = Money(3_000)

# これを超える申請は上長だけでなく経理の承認も要る
TWO_STEP_THRESHOLD = Money(30_000)

# これを超える申請は管理部門の承認も要る
THREE_STEP_THRESHOLD = Money(300_000)

# 発生日がこれより古い申請は受け付けない（決算をまたぐ遡及を防ぐ）
MAX_BACKDATE_DAYS = 90

CATEGORIES = ("transport", "lodging", "meals", "supplies", "other")
