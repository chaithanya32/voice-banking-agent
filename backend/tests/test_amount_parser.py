
from decimal import Decimal

import pytest

from app.services.amount_parser import parse_amount


@pytest.mark.parametrize(
    ("phrase", "expected"),
    [
        ("paanch sau", Decimal("500")),
        ("dedh hazaar", Decimal("1500")),
        ("dhai sau", Decimal("250")),
        ("sawa do lakh", Decimal("225000")),
        ("500 rupees", Decimal("500")),
        ("1500.50", Decimal("1500.50")),
    ],
)
def test_parse_supported_amounts(phrase, expected):
    assert parse_amount(phrase) == expected


@pytest.mark.parametrize(
    "phrase",
    [
        "",
        "maybe five hundred",
        "five hundred or fifteen hundred",
        "zero",
        "-500",
        "send 500 or maybe 1000",
        "pay 500 to Ravi",
        "500 and 1000",
    ],
)
def test_reject_unsupported_or_unsafe_amounts(phrase):
    with pytest.raises(ValueError):
        parse_amount(phrase)
