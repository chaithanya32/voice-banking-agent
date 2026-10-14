
from decimal import Decimal

from app.models import AuditLog, LedgerEntry
from app.services import payment_confirmation
from app.services.payment_confirmation import (
    confirm_payment,
    create_payment,
)


def test_confirmed_payment_creates_balanced_ledger_entries():
    payment = create_payment("Ravi Kumar", "500 rupees")

    confirm_payment(payment.payment_id, True)

    with payment_confirmation.SessionLocal() as session:
        entries = (
            session.query(LedgerEntry)
            .filter_by(payment_id=payment.payment_id)
            .all()
        )

        assert len(entries) == 2

        debit = next(e for e in entries if e.entry_type == "debit")
        credit = next(e for e in entries if e.entry_type == "credit")

        assert Decimal(str(debit.amount)) == Decimal("500.00")
        assert Decimal(str(credit.amount)) == Decimal("500.00")
        assert debit.account_name == "Customer Mock Account"
        assert credit.account_name == "Ravi Kumar"


def test_cancelled_payment_creates_no_ledger_entries():
    payment = create_payment("Ravi Kumar", "500")

    confirm_payment(payment.payment_id, False)

    with payment_confirmation.SessionLocal() as session:
        entries = (
            session.query(LedgerEntry)
            .filter_by(payment_id=payment.payment_id)
            .all()
        )

        assert entries == []


def test_payment_creation_and_confirmation_are_audited():
    payment = create_payment("Ravi Kumar", "500")

    confirm_payment(payment.payment_id, True)

    with payment_confirmation.SessionLocal() as session:
        logs = (
            session.query(AuditLog)
            .filter_by(payment_id=payment.payment_id)
            .all()
        )

        event_types = {log.event_type for log in logs}

        assert "payment_created" in event_types
        assert "payment_completed" in event_types


def test_cancelled_payment_is_audited():
    payment = create_payment("Ravi Kumar", "500")

    confirm_payment(payment.payment_id, False)

    with payment_confirmation.SessionLocal() as session:
        logs = (
            session.query(AuditLog)
            .filter_by(payment_id=payment.payment_id)
            .all()
        )

        event_types = {log.event_type for log in logs}

        assert "payment_created" in event_types
        assert "payment_cancelled" in event_types
        assert "payment_completed" not in event_types
