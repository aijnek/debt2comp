"""金額の表現。

金額は必ず最小通貨単位の整数で保持する。float を通すと丸め誤差が承認しきい値の
境界判定を揺らし、1円差で必要承認段数が変わる事故になるため、この型より内側に
float を持ち込まない。
"""

from __future__ import annotations

from dataclasses import dataclass

# 通貨コード -> 最小通貨単位の指数。JPY は補助単位を持たないので 0。
_EXPONENT = {"JPY": 0, "USD": 2, "EUR": 2}


@dataclass(frozen=True)
class Money:
    minor: int
    currency: str = "JPY"

    def __post_init__(self) -> None:
        if self.currency not in _EXPONENT:
            raise ValueError(f"未対応の通貨: {self.currency}")
        if isinstance(self.minor, bool) or not isinstance(self.minor, int):
            raise TypeError(f"金額は最小通貨単位の int で渡すこと: {self.minor!r}")

    @classmethod
    def parse(cls, text: str, currency: str = "JPY") -> Money:
        """人が入力した文字列を Money にする。'1,234.50' のような表記を受ける。"""
        if currency not in _EXPONENT:
            raise ValueError(f"未対応の通貨: {currency}")
        cleaned = text.strip().replace(",", "").replace(" ", "")
        if not cleaned:
            raise ValueError("金額が空です")
        exponent = _EXPONENT[currency]
        if "." in cleaned:
            whole, _, frac = cleaned.partition(".")
        else:
            whole, frac = cleaned, ""
        if not whole.lstrip("-").isdigit() or (frac and not frac.isdigit()):
            raise ValueError(f"金額として読めません: {text}")
        if len(frac) > exponent:
            raise ValueError(f"{currency} は小数点以下 {exponent} 桁までです: {text}")
        frac = frac.ljust(exponent, "0")
        sign = -1 if whole.startswith("-") else 1
        minor = int(whole.lstrip("-") or "0") * (10**exponent) + int(frac or "0")
        return cls(sign * minor, currency)

    def format(self) -> str:
        exponent = _EXPONENT[self.currency]
        sign = "-" if self.minor < 0 else ""
        units, sub = divmod(abs(self.minor), 10**exponent)
        body = f"{units:,}" if exponent == 0 else f"{units:,}.{sub:0{exponent}d}"
        return f"{sign}{body} {self.currency}"

    def _same_currency(self, other: Money) -> None:
        if self.currency != other.currency:
            raise ValueError(f"通貨が異なります: {self.currency} vs {other.currency}")

    def __add__(self, other: Money) -> Money:
        self._same_currency(other)
        return Money(self.minor + other.minor, self.currency)

    def __lt__(self, other: Money) -> bool:
        self._same_currency(other)
        return self.minor < other.minor

    def __le__(self, other: Money) -> bool:
        self._same_currency(other)
        return self.minor <= other.minor

    def __gt__(self, other: Money) -> bool:
        return other < self

    def __ge__(self, other: Money) -> bool:
        return other <= self

    def __str__(self) -> str:
        return self.format()
