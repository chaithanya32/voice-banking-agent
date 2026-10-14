
from decimal import Decimal

from app.services.payment_crosscheck import crosscheck_payment


def test_matching_details_are_approved():
    result = crosscheck_payment(
        "500 rupees", "Ravi Kumar",
        "500", "Ravi Kumar",
    )

    assert result.approved is True
    assert result.amount == Decimal("500")
    assert result.payee_name == "Ravi Kumar"


def test_amount_disagreement_is_rejected():
    result = crosscheck_payment(
        "500 rupees", "Ravi Kumar",
        "1500", "Ravi Kumar",
    )

    assert result.approved is False
    assert result.amount is None


def test_payee_disagreement_is_rejected():
    result = crosscheck_payment(
        "500", "Ravi Kumar",
        "500", "Priya Sharma",
    )

    assert result.approved is False
    assert result.payee_name is None


def test_missing_amount_is_rejected():
    result = crosscheck_payment(
        None, "Ravi Kumar",
        "500", "Ravi Kumar",
    )

    assert result.approved is False


def test_unknown_payee_is_rejected():
    result = crosscheck_payment(
        "500", "Unknown Person",
        "500", "Unknown Person",
    )

    assert result.approved is False


def test_equivalent_hinglish_amounts_are_approved():
    result = crosscheck_payment(
        "paanch sau", "Ravi Kumar",
        "500", "Ravi Kumar",
    )

    assert result.approved is True
    assert result.amount == Decimal("500")
