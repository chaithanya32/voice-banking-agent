
from dataclasses import dataclass
from decimal import Decimal

from app.services.amount_parser import parse_amount
from app.services.payee_matcher import Payee, match_payee
from app.services.payment_limits import MAX_TRANSACTION_AMOUNT


@dataclass(frozen=True)
class PaymentRequest:
    payee: Payee
    amount: Decimal


def validate_payment(
    payee_name: str,
    amount_text: str,
) -> PaymentRequest:
    """Validate payment details without executing a transfer."""

    payee = match_payee(payee_name)
    amount = parse_amount(amount_text)

    if amount <= 0:
        raise ValueError("Amount must be positive.")

    if amount.as_tuple().exponent < -2:
        raise ValueError("Amount cannot have more than two decimal places.")

    if amount > MAX_TRANSACTION_AMOUNT:
        raise ValueError(
            f"Amount exceeds the maximum transaction limit of "
            f"₹{MAX_TRANSACTION_AMOUNT}."
        )

    return PaymentRequest(
        payee=payee,
        amount=amount,
    )
