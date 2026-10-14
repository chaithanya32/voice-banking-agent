
from decimal import Decimal

import pytest

from app.services.payment_service import validate_payment


def test_validate_payment_success():
    request = validate_payment("Ravi Kumar", "500 rupees")

    assert request.payee.payee_id == "P001"
    assert request.payee.name == "Ravi Kumar"
    assert request.amount == Decimal("500")


def test_validate_hinglish_amount():
    request = validate_payment("Priya Sharma", "paanch sau")

    assert request.payee.payee_id == "P002"
    assert request.amount == Decimal("500")


def test_reject_unknown_payee():
    with pytest.raises(ValueError):
        validate_payment("Unknown Person", "500")


def test_reject_ambiguous_amount():
    with pytest.raises(ValueError):
        validate_payment("Ravi Kumar", "500 and 1000")


def test_reject_invalid_amount():
    with pytest.raises(ValueError):
        validate_payment("Ravi Kumar", "-500")
