
import pytest

from app.services.conversation import (
    ConversationState,
    handle_payment_turn,
)


def test_missing_amount_prompts_user():
    state = ConversationState()

    response = handle_payment_turn(
        state,
        payee_name="Ravi Kumar",
    )

    assert response["status"] == "awaiting_amount"
    assert "amount" in response["message"].lower()


def test_missing_payee_prompts_user():
    state = ConversationState()

    response = handle_payment_turn(
        state,
        amount_text="500 rupees",
    )

    assert response["status"] == "awaiting_payee"
    assert "pay" in response["message"].lower() or "who" in response["message"].lower()


def test_complete_details_request_confirmation():
    state = ConversationState()

    response = handle_payment_turn(
        state,
        payee_name="Ravi Kumar",
        amount_text="500 rupees",
    )

    assert response["status"] == "awaiting_confirmation"
    assert "Ravi Kumar" in response["message"]
    assert "500" in response["message"]


def test_confirmation_requires_explicit_yes_or_no():
    state = ConversationState()

    handle_payment_turn(
        state,
        payee_name="Ravi Kumar",
        amount_text="500 rupees",
    )

    response = handle_payment_turn(
        state,
        confirmation="maybe",
    )

    assert response["status"] == "awaiting_confirmation"


from app.models import LedgerEntry
from app.services import payment_confirmation


def test_payee_is_remembered_when_amount_is_missing():
    state = ConversationState()

    first = handle_payment_turn(state, payee_name="Ravi Kumar")
    second = handle_payment_turn(state, amount_text="500 rupees")

    assert first["status"] == "awaiting_amount"
    assert second["status"] == "awaiting_confirmation"
    assert "Ravi Kumar" in second["message"]
    assert "500" in second["message"]


def test_amount_is_remembered_when_payee_is_missing():
    state = ConversationState()

    first = handle_payment_turn(state, amount_text="500 rupees")
    second = handle_payment_turn(state, payee_name="Ravi Kumar")

    assert first["status"] == "awaiting_payee"
    assert second["status"] == "awaiting_confirmation"
    assert "Ravi Kumar" in second["message"]
    assert "500" in second["message"]


def test_yes_completes_payment_and_creates_ledger_entries():
    state = ConversationState()

    handle_payment_turn(
        state,
        payee_name="Ravi Kumar",
        amount_text="500 rupees",
    )

    response = handle_payment_turn(state, confirmation="yes")

    assert response["status"] == "completed"

    with payment_confirmation.SessionLocal() as session:
        entries = session.query(LedgerEntry).all()
        assert len(entries) == 2
        assert {entry.entry_type for entry in entries} == {
            "debit",
            "credit",
        }


def test_no_cancels_payment_without_ledger_entries():
    state = ConversationState()

    handle_payment_turn(
        state,
        payee_name="Ravi Kumar",
        amount_text="500 rupees",
    )

    response = handle_payment_turn(state, confirmation="no")

    assert response["status"] == "cancelled"

    with payment_confirmation.SessionLocal() as session:
        entries = session.query(LedgerEntry).all()
        assert len(entries) == 0