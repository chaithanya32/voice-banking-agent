
from dataclasses import dataclass
from datetime import datetime, time, timezone
from decimal import Decimal
from enum import Enum
from uuid import uuid4
from zoneinfo import ZoneInfo

from sqlalchemy import func

from app.database import SessionLocal
from app.models import AuditLog, LedgerEntry, PaymentRecord
from app.services.payment_limits import (
    DAILY_TRANSFER_LIMIT,
    MAX_TRANSACTION_AMOUNT,
)
from app.services.payment_service import validate_payment


OPENING_BALANCE = Decimal("25000.00")
CUSTOMER_ACCOUNT_NAME = "Customer Mock Account"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class PendingPayment:
    payment_id: str
    payee_id: str
    payee_name: str
    amount: Decimal
    status: PaymentStatus = PaymentStatus.PENDING


def _to_pending_payment(record: PaymentRecord) -> PendingPayment:
    amount = Decimal(
        format(Decimal(str(record.amount)).normalize(), "f")
    )

    return PendingPayment(
        payment_id=record.payment_id,
        payee_id=record.payee_id,
        payee_name=record.payee_name,
        amount=amount,
        status=PaymentStatus(record.status),
    )


def _add_audit_log(
    session,
    payment_id: str,
    event_type: str,
    details: str = "",
) -> None:
    session.add(
        AuditLog(
            payment_id=payment_id,
            event_type=event_type,
            details=details,
        )
    )


def _get_daily_completed_total(session) -> Decimal:
    """Return today's completed mock transfers using India Standard Time."""

    india_timezone = ZoneInfo("Asia/Kolkata")
    now_ist = datetime.now(india_timezone)

    day_start_ist = datetime.combine(
        now_ist.date(),
        time.min,
        tzinfo=india_timezone,
    )

    day_start_utc = day_start_ist.astimezone(timezone.utc).replace(
        tzinfo=None
    )

    completed_payments = (
        session.query(PaymentRecord)
        .filter(
            PaymentRecord.status == PaymentStatus.COMPLETED.value,
            PaymentRecord.created_at >= day_start_utc,
        )
        .all()
    )

    return sum(
        (
            Decimal(str(payment.amount))
            for payment in completed_payments
        ),
        Decimal("0.00"),
    )


def _get_current_balance_from_session(session) -> Decimal:
    """Calculate the customer's current balance from the ledger."""

    customer_credits = (
        session.query(
            func.coalesce(func.sum(LedgerEntry.amount), 0)
        )
        .filter(
            LedgerEntry.account_name == CUSTOMER_ACCOUNT_NAME,
            LedgerEntry.entry_type == "credit",
        )
        .scalar()
    )

    customer_debits = (
        session.query(
            func.coalesce(func.sum(LedgerEntry.amount), 0)
        )
        .filter(
            LedgerEntry.account_name == CUSTOMER_ACCOUNT_NAME,
            LedgerEntry.entry_type == "debit",
        )
        .scalar()
    )

    credits = Decimal(str(customer_credits or 0))
    debits = Decimal(str(customer_debits or 0))

    return (
        OPENING_BALANCE + credits - debits
    ).quantize(Decimal("0.01"))


def create_payment(
    payee_name: str,
    amount_text: str,
) -> PendingPayment:
    """Validate payment details and save a pending mock payment."""

    request = validate_payment(payee_name, amount_text)

    amount = Decimal(str(request.amount)).quantize(
        Decimal("0.01")
    )

    if amount <= 0:
        raise ValueError("Payment amount must be positive.")

    if amount > Decimal(str(MAX_TRANSACTION_AMOUNT)):
        raise ValueError(
            "Payment exceeds the maximum transaction limit."
        )

    record = PaymentRecord(
        payment_id=str(uuid4()),
        payee_id=request.payee.payee_id,
        payee_name=request.payee.name,
        amount=amount,
        status=PaymentStatus.PENDING.value,
    )

    with SessionLocal() as session:
        try:
            session.add(record)

            _add_audit_log(
                session,
                record.payment_id,
                "payment_created",
                f"Pending mock payment created for {record.payee_name}.",
            )

            session.commit()
            session.refresh(record)

            return _to_pending_payment(record)

        except Exception:
            session.rollback()
            raise


def confirm_payment(
    payment_id: str,
    confirmed: bool,
) -> PendingPayment:
    """
    Confirm or cancel a pending mock payment.

    Validate the daily transfer limit and available balance before
    changing the payment status or adding ledger entries.
    """

    with SessionLocal() as session:
        try:
            record = session.get(PaymentRecord, payment_id)

            if record is None:
                raise ValueError("Payment not found.")

            # Prevent duplicate confirmation or cancellation.
            if record.status != PaymentStatus.PENDING.value:
                raise ValueError("Payment is no longer pending.")

            if not confirmed:
                record.status = PaymentStatus.CANCELLED.value

                _add_audit_log(
                    session,
                    record.payment_id,
                    "payment_cancelled",
                    "Pending mock payment was cancelled.",
                )

                session.commit()
                session.refresh(record)

                return _to_pending_payment(record)

            amount = Decimal(str(record.amount)).quantize(
                Decimal("0.01")
            )

            if amount <= 0:
                raise ValueError("Payment amount must be positive.")

            if amount > Decimal(str(MAX_TRANSACTION_AMOUNT)):
                raise ValueError(
                    "Payment exceeds the maximum transaction limit."
                )

            # Check the daily limit first to preserve the expected
            # error when both the daily limit and balance are exceeded.
            daily_total = _get_daily_completed_total(session)

            if (
                daily_total + amount
                > Decimal(str(DAILY_TRANSFER_LIMIT))
            ):
                raise ValueError(
                    "Daily transfer limit exceeded. "
                    "The payment remains pending."
                )

            # Check the available balance before completing the payment.
            balance = _get_current_balance_from_session(session)

            if amount > balance:
                raise ValueError(
                    f"Insufficient balance. Your available balance is "
                    f"INR {balance:.2f}, but this payment requires "
                    f"INR {amount:.2f}. The payment remains pending."
                )

            # All validations passed. Complete the payment and update
            # both sides of the ledger within the same transaction.
            record.status = PaymentStatus.COMPLETED.value

            session.add_all(
                [
                    LedgerEntry(
                        payment_id=record.payment_id,
                        account_name=CUSTOMER_ACCOUNT_NAME,
                        entry_type="debit",
                        amount=amount,
                    ),
                    LedgerEntry(
                        payment_id=record.payment_id,
                        account_name=record.payee_name,
                        entry_type="credit",
                        amount=amount,
                    ),
                ]
            )

            _add_audit_log(
                session,
                record.payment_id,
                "payment_completed",
                f"Mock payment of INR {amount:.2f} completed.",
            )

            session.commit()
            session.refresh(record)

            return _to_pending_payment(record)

        except Exception:
            session.rollback()
            raise


def get_current_balance() -> Decimal:
    """
    Calculate the current demo balance from the persisted SQLite ledger.

    Balance = opening balance + customer credits - customer debits.
    Payee credits are excluded because they belong to other accounts.
    """

    with SessionLocal() as session:
        return _get_current_balance_from_session(session)
