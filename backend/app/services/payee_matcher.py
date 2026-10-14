
from dataclasses import dataclass


@dataclass(frozen=True)
class Payee:
    payee_id: str
    name: str


MOCK_PAYEES = [
    Payee(payee_id="P001", name="Ravi Kumar"),
    Payee(payee_id="P002", name="Priya Sharma"),
    Payee(payee_id="P003", name="Rahul Reddy"),
    Payee(payee_id="P004", name="chaitanya"),
]


def match_payee(name: str) -> Payee:
    """Match a recipient, ignoring case and spacing differences."""

    if not isinstance(name, str) or not name.strip():
        raise ValueError("Payee name is required.")

    normalized = "".join(name.casefold().split())

    matches = [
        payee
        for payee in MOCK_PAYEES
        if "".join(payee.name.casefold().split()) == normalized
    ]

    if not matches:
        raise ValueError("Payee not found.")

    if len(matches) > 1:
        raise ValueError("Ambiguous payee. Please clarify the recipient.")

    return matches[0]
