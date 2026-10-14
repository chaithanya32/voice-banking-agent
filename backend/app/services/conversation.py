
import re
from dataclasses import dataclass
from typing import Optional

from app.services.payment_confirmation import (
    confirm_payment,
    create_payment,
)


@dataclass
class ConversationState:
    payee_name: Optional[str] = None
    amount_text: Optional[str] = None
    pending_payment_id: Optional[str] = None


def handle_payment_turn(
    state: ConversationState,
    payee_name: Optional[str] = None,
    amount_text: Optional[str] = None,
    confirmation: Optional[str] = None,
) -> dict:
    """Handle one turn in a mock payment conversation."""

    if state.pending_payment_id:
        answer = re.sub(
            r"[^\w\s]",
            " ",
            (confirmation or "").casefold(),
        )
        answer = " ".join(answer.split())

        # Accept repeated affirmative words from speech recognition,
        # such as "Yes. Yes." or "yes yes".
        affirmative_words = {"yes", "y", "confirm", "confirmed"}

        if answer and all(
            word in affirmative_words for word in answer.split()
        ):
            answer = "yes"

        if answer in ("yes", "y", "confirm", "confirmed"):
            try:
                payment = confirm_payment(
                    state.pending_payment_id,
                    confirmed=True,
                )

            except ValueError as error:
                error_message = str(error)

                if (
                    "Daily transfer limit exceeded" in error_message
                    or "maximum transaction limit" in error_message
                ):
                    # Automatically cancel when a known payment limit
                    # prevents completion.
                    payment = confirm_payment(
                        state.pending_payment_id,
                        confirmed=False,
                    )

                    state.pending_payment_id = None
                    state.payee_name = None
                    state.amount_text = None

                    # Remove the contradictory pending-status sentence.
                    reason = error_message.replace(
                        " The payment remains pending.", ""
                    )

                    return {
                        "status": "cancelled",
                        "message": (
                            f"Payment to {payment.payee_name} was "
                            f"automatically cancelled. "
                            f"Reason: {reason}"
                        ),
                    }

                # Preserve the pending state for unexpected validation
                # errors so they can be investigated or retried.
                raise

            state.pending_payment_id = None
            state.payee_name = None
            state.amount_text = None

            return {
                "status": "completed",
                "message": (
                    f"Mock payment of {payment.amount} rupees to "
                    f"{payment.payee_name} completed."
                ),
            }

        if answer in (
            "no",
            "n",
            "cancel",
            "cancel payment",
            "cancel the payment",
            "cancel this payment",
            "cancelled the payment",
            "cancelled payment",
            "cancel the transaction",
            "stop payment",
        ):
            payment = confirm_payment(
                state.pending_payment_id,
                confirmed=False,
            )

            state.pending_payment_id = None
            state.payee_name = None
            state.amount_text = None

            return {
                "status": "cancelled",
                "message": (
                    f"Payment to {payment.payee_name} cancelled."
                ),
            }

        return {
            "status": "awaiting_confirmation",
            "message": "Please say yes to confirm or no to cancel.",
        }

    if payee_name and payee_name.strip():
        state.payee_name = payee_name.strip()

    if amount_text and amount_text.strip():
        state.amount_text = amount_text.strip()

    if not state.payee_name:
        return {
            "status": "awaiting_payee",
            "message": "Who would you like to pay?",
        }

    if not state.amount_text:
        return {
            "status": "awaiting_amount",
            "message": (
                f"What amount would you like to pay {state.payee_name}?"
            ),
        }

    try:
        payment = create_payment(
            state.payee_name,
            state.amount_text,
        )
    except ValueError:
        # Payment creation failed before a pending payment was created.
        state.payee_name = None
        state.amount_text = None
        raise

    state.pending_payment_id = payment.payment_id

    return {
        "status": "awaiting_confirmation",
        "message": (
            f"Please confirm: pay {payment.amount} rupees to "
            f"{payment.payee_name}. Say yes to confirm or no to cancel."
        ),
    }