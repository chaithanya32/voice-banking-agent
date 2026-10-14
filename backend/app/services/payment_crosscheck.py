
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Optional

from app.services.amount_parser import parse_amount
from app.services.payee_matcher import match_payee


@dataclass(frozen=True)
class CrosscheckResult:
    approved: bool
    amount: Optional[Decimal]
    payee_name: Optional[str]
    reason: str


def _normalize_amount(value: Optional[str]) -> Optional[Decimal]:
    if not isinstance(value, str) or not value.strip():
        return None

    try:
        amount = parse_amount(value.strip())
    except (ValueError, InvalidOperation):
        return None

    return amount if amount > 0 else None


def _normalize_payee(value: Optional[str]) -> Optional[str]:
    if not isinstance(value, str) or not value.strip():
        return None

    try:
        return match_payee(value.strip()).name
    except ValueError:
        return None


def crosscheck_payment(
    deterministic_amount: Optional[str],
    deterministic_payee: Optional[str],
    independent_amount: Optional[str],
    independent_payee: Optional[str],
) -> CrosscheckResult:
    """Approve extracted details only when both interpretations agree."""

    amount_a = _normalize_amount(deterministic_amount)
    amount_b = _normalize_amount(independent_amount)
    payee_a = _normalize_payee(deterministic_payee)
    payee_b = _normalize_payee(independent_payee)

    if amount_a is None or amount_b is None:
        return CrosscheckResult(
            False, None, None,
            "Amount could not be independently verified.",
        )

    if payee_a is None or payee_b is None:
        return CrosscheckResult(
            False, None, None,
            "Recipient could not be independently verified.",
        )

    if amount_a != amount_b:
        return CrosscheckResult(
            False, None, None,
            "The amount interpretations disagree.",
        )

    if payee_a != payee_b:
        return CrosscheckResult(
            False, None, None,
            "The recipient interpretations disagree.",
        )

    return CrosscheckResult(
        approved=True,
        amount=amount_a,
        payee_name=payee_a,
        reason="Amount and recipient interpretations agree.",
    )
