
import pytest

from app.models import LedgerEntry
from app.services import payment_confirmation
from app.services.payment_confirmation import (
    confirm_payment,
    create_payment,
)


def test_reject_payment_above_transaction_limit():
    with pytest.raises(ValueError, match="maximum transaction limit"):
        create_payment("Ravi Kumar", "10001 rupees")


def test_payment_within_transaction_limit_is_allowed():
    payment = create_payment("Ravi Kumar", "10000 rupees")

    assert str(payment.amount) == "10000"
    assert payment.status.value == "pending"


def test_daily_limit_is_enforced_at_confirmation():
    # Complete transfers totalling the ₹25,000 daily limit.
    for amount in ("10000", "10000", "5000"):
        payment = create_payment("Ravi Kumar", amount)
        confirm_payment(payment.payment_id, True)

    # This payment can be created but must not be completed.
    extra_payment = create_payment("Ravi Kumar", "1")

    with pytest.raises(ValueError, match="Daily transfer limit exceeded"):
        confirm_payment(extra_payment.payment_id, True)

    # The rejected confirmation must not create ledger entries.
    with payment_confirmation.SessionLocal() as session:
        entries = (
            session.query(LedgerEntry)
            .filter_by(payment_id=extra_payment.payment_id)
            .all()
        )

        assert entries == []


def test_payment_can_be_cancelled_after_daily_limit_is_reached():
    for amount in ("10000", "10000", "5000"):
        payment = create_payment("Ravi Kumar", amount)
        confirm_payment(payment.payment_id, True)

    extra_payment = create_payment("Ravi Kumar", "1")
    result = confirm_payment(extra_payment.payment_id, False)

    assert result.status.value == "cancelled"
