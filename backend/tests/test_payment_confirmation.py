import pytest

from app.services.payment_confirmation import (
    PaymentStatus,
    confirm_payment,
    create_payment,
)


def test_create_pending_payment():
    payment = create_payment("Ravi Kumar", "500 rupees")

    assert payment.status == PaymentStatus.PENDING
    assert payment.payee_name == "Ravi Kumar"
    assert str(payment.amount) == "500"


def test_confirm_pending_payment():
    payment = create_payment("Ravi Kumar", "500")

    result = confirm_payment(payment.payment_id, True)

    assert result.status == PaymentStatus.COMPLETED


def test_cancel_pending_payment():
    payment = create_payment("Ravi Kumar", "500")

    result = confirm_payment(payment.payment_id, False)

    assert result.status == PaymentStatus.CANCELLED


def test_cannot_confirm_completed_payment_twice():
    payment = create_payment("Ravi Kumar", "500")
    confirm_payment(payment.payment_id, True)

    with pytest.raises(ValueError):
        confirm_payment(payment.payment_id, True)


def test_cannot_confirm_cancelled_payment():
    payment = create_payment("Ravi Kumar", "500")
    confirm_payment(payment.payment_id, False)

    with pytest.raises(ValueError):
        confirm_payment(payment.payment_id, True)


def test_reject_unknown_payment_id():
    with pytest.raises(ValueError):
        confirm_payment("unknown-id", True)
