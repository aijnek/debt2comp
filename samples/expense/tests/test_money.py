import pytest

from app.money import Money


def test_parse_jpy_has_no_minor_unit():
    assert Money.parse("1,200") == Money(1200, "JPY")
    with pytest.raises(ValueError):
        Money.parse("1200.5")


def test_parse_usd_keeps_cents():
    assert Money.parse("12.34", "USD") == Money(1234, "USD")
    assert Money.parse("12.3", "USD") == Money(1230, "USD")


def test_float_is_not_accepted_as_amount():
    with pytest.raises(TypeError):
        Money(1200.0)


def test_comparison_requires_same_currency():
    assert Money(100) < Money(200)
    with pytest.raises(ValueError):
        Money(100, "JPY") < Money(100, "USD")


def test_format_is_readable():
    assert Money(1234567).format() == "1,234,567 JPY"
    assert Money(1234, "USD").format() == "12.34 USD"
