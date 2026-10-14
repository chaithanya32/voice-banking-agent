import os
import re
import tempfile
from datetime import timezone
from typing import Optional
from uuid import UUID
from zoneinfo import ZoneInfo
from dataclasses import dataclass
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import desc, func
from app.services.payment_crosscheck import crosscheck_payment
from app.database import Base, engine, SessionLocal
from app.models import PaymentRecord
from app.services.conversation import (
    ConversationState,
    handle_payment_turn,
)
from app.services.llm_intent import interpret_payment_intent
from app.services.payee_matcher import MOCK_PAYEES, match_payee
from app.services.payment_confirmation import (
    PaymentStatus,
    confirm_payment,
    create_payment,
    get_current_balance,
)
from app.services.speech_to_text import transcribe_audio

from fastapi import Depends
from pydantic import BaseModel, EmailStr, Field


from app.services.auth import (
    authenticate_customer,
    create_access_token,
    get_current_customer,
    register_customer,
    set_customer_pin,
    verify_customer_pin,
)
from app.models import Customer



Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Voice Banking Agent",
    description="A safety-first mock voice banking application",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://voxbank-89tingj4a-chaithanyas-projects-4a76b4bf.vercel.app",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CreatePaymentRequest(BaseModel):
    payee_name: str = Field(min_length=1, max_length=100)
    amount_text: str = Field(min_length=1, max_length=200)


class ConfirmPaymentRequest(BaseModel):
    confirmed: bool
    pin: Optional[str] = None


class ConversationRequest(BaseModel):
    conversation_id: str = Field(min_length=1, max_length=100)
    payee_name: Optional[str] = Field(default=None, max_length=100)
    amount_text: Optional[str] = Field(default=None, max_length=200)
    confirmation: Optional[str] = Field(default=None, max_length=50)


class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


@app.post("/auth/register", status_code=201)
def register_endpoint(payload: RegisterRequest):
    try:
        customer = register_customer(
            name=payload.name,
            email=str(payload.email),
            password=payload.password,
        )
        return {
            "message": "Account created successfully.",
            "customer": {
                "id": customer.id,
                "name": customer.name,
                "email": customer.email,
            },
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/auth/login")
def login_endpoint(payload: LoginRequest):
    try:
        customer = authenticate_customer(
            email=str(payload.email),
            password=payload.password,
        )
    except ValueError:
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password.",
        )

    return {
        "access_token": create_access_token(customer.id),
        "token_type": "bearer",
        "customer": {
            "id": customer.id,
            "name": customer.name,
            "email": customer.email,
        },
    }


@app.get("/auth/me")
def current_customer_endpoint(
    customer: Customer = Depends(get_current_customer),
):
    return {
        "id": customer.id,
        "name": customer.name,
        "email": customer.email,
    }

class SetPinRequest(BaseModel):
    pin: str = Field(min_length=4, max_length=6, pattern=r"^\d{4,6}$")


class VerifyPinRequest(BaseModel):
    pin: str = Field(min_length=4, max_length=6, pattern=r"^\d{4,6}$")


@app.post("/auth/pin/set")
def set_pin_endpoint(
    request: SetPinRequest,
    customer: Customer = Depends(get_current_customer),
):
    try:
        set_customer_pin(customer.id, request.pin)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"message": "PIN set successfully."}


@app.post("/auth/pin/verify")
def verify_pin_endpoint(
    request: VerifyPinRequest,
    customer: Customer = Depends(get_current_customer),
):
    try:
        verify_customer_pin(customer.id, request.pin)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"verified": True, "message": "PIN verified successfully."}


conversation_states = {}


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "voice-banking-agent",
    }


@app.get("/balance")
def get_balance():
    balance = get_current_balance()
    return {"balance": str(balance)}


@app.get("/payments")
def get_payment_history():
    """Return recent mock payments and the demo account summary."""

    with SessionLocal() as session:
        payments = (
            session.query(PaymentRecord)
            .order_by(desc(PaymentRecord.created_at))
            .limit(20)
            .all()
        )

        completed_total = (
            session.query(func.coalesce(func.sum(PaymentRecord.amount), 0))
            .filter(
                PaymentRecord.status == PaymentStatus.COMPLETED.value
            )
            .scalar()
        )

        transactions = [
            {
                "payment_id": payment.payment_id,
                "payee_name": payment.payee_name,
                "amount": str(payment.amount),
                "currency": "INR",
                "status": payment.status,
                "created_at": (
                    payment.created_at.replace(tzinfo=timezone.utc)
                    if payment.created_at.tzinfo is None
                    else payment.created_at
                ).astimezone(ZoneInfo("Asia/Kolkata")).isoformat(),
            }
            for payment in payments
        ]

        return {
            "transactions": transactions,
            "completed_transfers_total": str(completed_total),
            "currency": "INR",
        }


@app.post("/payments", status_code=201)
def create_payment_endpoint(request: CreatePaymentRequest):
    try:
        payment = create_payment(
            request.payee_name,
            request.amount_text,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return {
        "payment_id": payment.payment_id,
        "payee_name": payment.payee_name,
        "amount": str(payment.amount),
        "currency": "INR",
        "status": payment.status.value,
        "confirmation_message": (
            f"Please confirm: transfer ₹{payment.amount} "
            f"to {payment.payee_name}?"
        ),
    }


@app.post("/payments/{payment_id}/confirm")
def confirm_payment_endpoint(
    payment_id: UUID,
    request: ConfirmPaymentRequest,
):
    try:
        payment = confirm_payment(
            str(payment_id),
            request.confirmed,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return {
        "payment_id": payment.payment_id,
        "payee_name": payment.payee_name,
        "amount": str(payment.amount),
        "currency": "INR",
        "status": payment.status.value,
        "message": (
            "Mock payment completed."
            if payment.status == PaymentStatus.COMPLETED
            else "Payment cancelled."
        ),
    }


@app.post("/conversation")
def conversation_endpoint(request: ConversationRequest):
    conversation_id = request.conversation_id.strip()

    if not conversation_id:
        raise HTTPException(
            status_code=400,
            detail="Conversation ID is required.",
        )

    state = conversation_states.setdefault(
        conversation_id,
        ConversationState(),
    )

    try:
        return handle_payment_turn(
            state,
            payee_name=request.payee_name,
            amount_text=request.amount_text,
            confirmation=request.confirmation,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


def parse_voice_payment_request(spoken_text: str):
    """Extract an amount and recipient from common English payment phrases."""

    text = spoken_text.strip().rstrip(".!?")

    text = re.sub(
        r"^(?:please\s+)?(?:i want to\s+|i'd like to\s+|"
        r"i would like to\s+|can you\s+|could you\s+)?",
        "",
        text,
        flags=re.IGNORECASE,
    )

    action = re.match(r"^(?:pay|send|transfer)\s+(.+)$", text, re.I)
    if not action:
        return None

    remainder = action.group(1).strip()

    # Example: "send 500 rupees to Ravi Kumar"
    match = re.match(r"^(.+?)\s+to\s+(.+)$", remainder, re.I)
    if match:
        amount = match.group(1).strip()
        payee = match.group(2).strip()

        if amount.casefold() in {
            "money",
            "some money",
            "an amount",
            "some amount",
        }:
            amount = None
        else:
            amount = re.sub(
                r"\s*(?:rupees?|rs\.?|₹)\s*$",
                "",
                amount,
                flags=re.I,
            ).strip()

        return amount or None, payee or None

    # Example: "pay Rahul Reddy 500 rupees"
    for registered_payee in sorted(
        MOCK_PAYEES,
        key=lambda person: len(person.name),
        reverse=True,
    ):
        name = registered_payee.name
        if remainder.casefold().startswith(name.casefold()):
            tail = remainder[len(name):].strip()
            amount = re.sub(
                r"^(?:rupees?|rs\.?|₹)\s*",
                "",
                tail,
                flags=re.I,
            )
            amount = re.sub(
                r"\s*(?:rupees?|rs\.?|₹)\s*$",
                "",
                amount,
                flags=re.I,
            ).strip()
            return amount or None, name

    # Example: "send 500 rupees" — recipient is missing.
    amount_only = re.fullmatch(
        r"(?:₹\s*)?([\d,]+(?:\.\d{1,2})?)\s*"
        r"(?:rupees?|rs\.?)?",
        remainder,
        re.I,
    )
    if amount_only:
        return amount_only.group(1), None

    # Unknown recipient; let the caller ask for clarification.
    return None, remainder


def normalize_llm_amount(value):
    """Accept only valid positive numeric amounts from the LLM."""

    if not isinstance(value, str):
        return None

    amount = value.strip().replace(",", "")

    if not re.fullmatch(r"\d+(?:\.\d{1,2})?", amount):
        return None

    try:
        numeric_amount = float(amount)
    except ValueError:
        return None

    if numeric_amount <= 0:
        return None

    return amount


def normalize_llm_payee(value):
    """Match an LLM recipient to an actual registered payee."""

    if not isinstance(value, str) or not value.strip():
        return None

    try:
        return match_payee(value.strip())
    except ValueError as exc:
        if str(exc) == "Payee not found.":
            return None
        raise


@app.post("/voice")
async def voice_endpoint(
    conversation_id: str = Form(...),
    file: UploadFile = File(...),
):
    allowed_types = {
        "audio/mpeg",
        "audio/mp4",
        "audio/x-m4a",
        "audio/wav",
        "audio/wave",
        "audio/x-wav",
        "audio/webm",
    }

    content_type = (
        (file.content_type or "")
        .split(";", 1)[0]
        .strip()
        .lower()
    )

    if content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported audio format: {file.content_type}",
        )

    conversation_id = conversation_id.strip()

    if not conversation_id:
        raise HTTPException(
            status_code=400,
            detail="Conversation ID is required.",
        )

    suffix = os.path.splitext(file.filename or "")[1] or ".m4a"
    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            suffix=suffix,
            delete=False,
        ) as temp_file:
            temp_path = temp_file.name
            temp_file.write(await file.read())

        text = transcribe_audio(temp_path)
        spoken_text = (text or "").strip()

        normalized_text = spoken_text.casefold().strip(
            " \t\r\n.!?,"
        )

        state = conversation_states.setdefault(
            conversation_id,
            ConversationState(),
        )

        print("\n========== VOICE DEBUG ==========")
        print("DEBUG conversation ID:", repr(conversation_id))
        print("DEBUG recognized speech:", repr(spoken_text))
        print("DEBUG existing payee:", repr(state.payee_name))
        print("DEBUG existing amount:", repr(state.amount_text))
        print(
            "DEBUG existing pending payment ID:",
            repr(state.pending_payment_id),
        )

        # Reuse Gemini's result when the conversation is awaiting
        # an amount or recipient, avoiding duplicate calls.
        llm_result = None
        llm_result_loaded = False

        def get_llm_result():
            nonlocal llm_result, llm_result_loaded

            if not llm_result_loaded:
                llm_result = interpret_payment_intent(spoken_text)
                llm_result_loaded = True

            return llm_result

        def finish(result):
            print("DEBUG conversation result:", result)
            print("========== END VOICE DEBUG ==========\n")

            return {
                "transcribed_text": text,
                "conversation": result,
            }

        def clear_incomplete_payment():
            state.payee_name = None
            state.amount_text = None
            state.pending_payment_id = None

        def cancellation_result():
            clear_incomplete_payment()

            return {
                "status": "cancelled",
                "message": (
                    "Payment request cancelled. "
                    "No money was transferred."
                ),
            }

        # Handle an existing payment awaiting confirmation.
        # Do not bypass the explicit confirmation requirement.
        if state.pending_payment_id:
            if re.match(
                r"^\s*(?:please\s+)?(?:pay|send|transfer)\b",
                spoken_text,
                re.IGNORECASE,
            ):
                result = {
                    "status": "awaiting_confirmation",
                    "message": (
                        "You already have a pending payment. "
                        "Please say yes to confirm it or no to cancel it "
                        "before starting another payment."
                    ),
                }
            else:
                result = handle_payment_turn(
                    state,
                    confirmation=normalized_text,
                )

            return finish(result)

        # Handle cancellation before asking for more payment details.
        # This fixes cancellation getting interpreted as an amount.
        has_incomplete_payment = bool(
            (state.payee_name and not state.amount_text)
            or (state.amount_text and not state.payee_name)
        )

        if has_incomplete_payment:
            # Numeric amount follow-ups can be parsed directly.
            cleaned_speech = spoken_text.strip().rstrip(".!?")

            numeric_amount_match = re.fullmatch(
                r"(?:₹\s*)?([\d,]+(?:\.\d{1,2})?)\s*"
                r"(?:rupees?|rs\.?)?",
                cleaned_speech,
                re.IGNORECASE,
            )

            if not numeric_amount_match:
                partial_result = get_llm_result()

                print(
                    "DEBUG Gemini partial conversation intent:",
                    repr(partial_result),
                )

                if (
                    isinstance(partial_result, dict)
                    and partial_result.get("intent") == "cancellation"
                ):
                    return finish(cancellation_result())

        # Handle amount follow-up when a recipient is already stored.
        if state.payee_name and not state.amount_text:
            cleaned_speech = spoken_text.strip().rstrip(".!?")

            amount_match = re.fullmatch(
                r"(?:₹\s*)?([\d,]+(?:\.\d{1,2})?)\s*"
                r"(?:rupees?|rs\.?)?",
                cleaned_speech,
                re.IGNORECASE,
            )

            amount_text = None
            raw_llm_amount = None

            if amount_match:
                amount_text = amount_match.group(1).replace(",", "")
            else:
                # Reuse the Gemini result obtained above.
                llm_amount_result = get_llm_result()

                print(
                    "DEBUG Gemini amount follow-up:",
                    repr(llm_amount_result),
                )

                if isinstance(llm_amount_result, dict):
                    raw_llm_amount = llm_amount_result.get(
                        "amount_text"
                    )
                    amount_text = normalize_llm_amount(
                        raw_llm_amount
                    )

            # Reject a recognized zero or negative amount before
            # normalize_llm_amount discards it.
            raw_amount_for_check = (
                raw_llm_amount.strip().replace(",", "")
                if isinstance(raw_llm_amount, str)
                else None
            )

            if (
                raw_amount_for_check
                and re.fullmatch(
                    r"-?\d+(?:\.\d{1,2})?",
                    raw_amount_for_check,
                )
                and float(raw_amount_for_check) <= 0
            ):
                result = {
                    "status": "awaiting_amount",
                    "message": (
                        "The amount must be greater than zero. "
                        "Please say a valid amount, such as 500 rupees."
                    ),
                }

                print(
                    "DEBUG rejected non-positive amount:",
                    raw_amount_for_check,
                )

                return finish(result)

            # Direct numeric amounts also need a positivity check.
            if amount_match:
                numeric_amount = float(
                    amount_text.replace(",", "")
                )

                if numeric_amount <= 0:
                    result = {
                        "status": "awaiting_amount",
                        "message": (
                            "The amount must be greater than zero. "
                            "Please say a valid amount, such as 500 rupees."
                        ),
                    }

                    print(
                        "DEBUG rejected non-positive amount:",
                        amount_text,
                    )

                    return finish(result)

            if amount_text is None:
                result = {
                    "status": "awaiting_amount",
                    "message": (
                        "I couldn't understand that amount. Please say "
                        "a positive amount, such as 500 rupees or "
                        "five hundred rupees."
                    ),
                }

                print(
                    "DEBUG invalid or unrecognized amount:",
                    repr(spoken_text),
                )

                return finish(result)

            # Payment service validates limits and creates a pending
            # payment. It must not complete the payment automatically.
            result = handle_payment_turn(
                state,
                amount_text=f"{amount_text} rupees",
            )

            print("DEBUG amount follow-up:", amount_text)
            return finish(result)

        # Handle recipient follow-up when an amount is already stored.
        if state.amount_text and not state.payee_name:
            try:
                matched_payee = match_payee(
                    spoken_text.strip(" \t\r\n.!?,")
                )
            except ValueError as exc:
                if str(exc) != "Payee not found.":
                    raise

                matched_payee = None

            if matched_payee:
                result = handle_payment_turn(
                    state,
                    payee_name=matched_payee.name,
                )

                print(
                    "DEBUG recipient follow-up:",
                    matched_payee.name,
                )

                return finish(result)

            # If direct matching fails, let Gemini interpret the name.
            recipient_result = get_llm_result()

            if (
                isinstance(recipient_result, dict)
                and recipient_result.get("intent") == "cancellation"
            ):
                return finish(cancellation_result())

            if (
                isinstance(recipient_result, dict)
                and recipient_result.get("intent") == "payment_request"
            ):
                payee_value = recipient_result.get("payee_name")
                matched_payee = normalize_llm_payee(payee_value)

                if matched_payee:
                    result = handle_payment_turn(
                        state,
                        payee_name=matched_payee.name,
                    )

                    print(
                        "DEBUG Gemini recipient follow-up:",
                        matched_payee.name,
                    )

                    return finish(result)

            result = {
                "status": "awaiting_recipient",
                "message": (
                    "I couldn't identify that recipient. "
                    "Please say the name of a registered recipient."
                ),
                "registered_payees": [
                    payee.name for payee in MOCK_PAYEES
                ],
            }

            return finish(result)

        # Stop if a new request mentions multiple registered recipients.
        spoken_lower = spoken_text.casefold()

        mentioned_payees = [
            payee.name
            for payee in MOCK_PAYEES
            if payee.name.casefold() in spoken_lower
        ]

        if len(mentioned_payees) > 1:
            result = {
                "status": "needs_clarification",
                "message": (
                    "I heard more than one recipient: "
                    + " and ".join(mentioned_payees)
                    + ". Who would you like to pay?"
                ),
                "registered_payees": [
                    payee.name for payee in MOCK_PAYEES
                ],
            }

            print(
                "DEBUG conflicting recipients:",
                mentioned_payees,
            )

            return finish(result)

        # Try the deterministic English parser first.
        parsed_request = parse_voice_payment_request(spoken_text)

        if parsed_request:
            amount_phrase, payee_name = parsed_request
            matched_payee = None

            if payee_name:
                try:
                    matched_payee = match_payee(payee_name)
                except ValueError as exc:
                    if str(exc) != "Payee not found.":
                        raise

                    state.payee_name = None
                    state.amount_text = (
                        f"{amount_phrase} rupees"
                        if amount_phrase
                        else None
                    )

                    result = {
                        "status": "needs_clarification",
                        "message": (
                            f"I couldn't match '{payee_name}' to a "
                            "registered recipient. Please say the "
                            "registered recipient's name."
                        ),
                        "registered_payees": [
                            payee.name for payee in MOCK_PAYEES
                        ],
                    }

                    print(
                        "DEBUG unknown recipient:",
                        repr(payee_name),
                    )

                    return finish(result)

            if matched_payee and not amount_phrase:
                result = handle_payment_turn(
                    state,
                    payee_name=matched_payee.name,
                )

                print(
                    "DEBUG recipient recognized:",
                    matched_payee.name,
                )

                return finish(result)

            if amount_phrase and not matched_payee:
                # Reject zero/negative amounts before storing them.
                try:
                    parsed_amount = float(
                        amount_phrase.replace(",", "")
                    )
                except (TypeError, ValueError):
                    parsed_amount = None

                if parsed_amount is not None and parsed_amount <= 0:
                    result = {
                        "status": "awaiting_amount",
                        "message": (
                            "The amount must be greater than zero. "
                            "Please say a valid amount, such as 500 rupees."
                        ),
                    }

                    return finish(result)

                state.payee_name = None
                state.amount_text = f"{amount_phrase} rupees"

                result = handle_payment_turn(state)

                print(
                    "DEBUG amount recognized:",
                    repr(amount_phrase),
                )

                return finish(result)

            if amount_phrase and matched_payee:
                try:
                    parsed_amount = float(
                        amount_phrase.replace(",", "")
                    )
                except (TypeError, ValueError):
                    parsed_amount = None

                if parsed_amount is not None and parsed_amount <= 0:
                    result = {
                        "status": "awaiting_amount",
                        "message": (
                            "The amount must be greater than zero. "
                            "Please say a valid amount, such as 500 rupees."
                        ),
                    }

                    return finish(result)

                result = handle_payment_turn(
                    state,
                    payee_name=matched_payee.name,
                    amount_text=f"{amount_phrase} rupees",
                )

                print("DEBUG deterministic parser result:", result)
                return finish(result)

        # Recognize a registered recipient spoken by itself.
        standalone_name = spoken_text.strip(" \t\r\n.!?,")
        matched_standalone_payee = None

        try:
            matched_standalone_payee = match_payee(standalone_name)
        except ValueError as exc:
            if str(exc) != "Payee not found.":
                raise

        if matched_standalone_payee:
            result = handle_payment_turn(
                state,
                payee_name=matched_standalone_payee.name,
            )

            print(
                "DEBUG standalone recipient:",
                matched_standalone_payee.name,
            )

            return finish(result)

        # Gemini fallback for Hindi and Hinglish.
        llm_result = get_llm_result()

        print("DEBUG Gemini intent:", repr(llm_result))

        if isinstance(llm_result, dict):
            raw_amount = llm_result.get("amount_text")

            print(
                "DEBUG normalized amount/payee:",
                repr(
                    (
                        normalize_llm_amount(raw_amount),
                        llm_result.get("payee_name"),
                    )
                ),
            )

            # Detect numeric zero/negative amounts before normalization.
            raw_numeric_amount = (
                raw_amount.strip().replace(",", "")
                if isinstance(raw_amount, str)
                else None
            )

            if (
                llm_result.get("intent") == "payment_request"
                and raw_numeric_amount
                and re.fullmatch(
                    r"-?\d+(?:\.\d{1,2})?",
                    raw_numeric_amount,
                )
                and float(raw_numeric_amount) <= 0
            ):
                result = {
                    "status": "awaiting_amount",
                    "message": (
                        "The amount must be greater than zero. "
                        "Please say a valid amount, such as 500 rupees."
                    ),
                }

                print(
                    "DEBUG rejected non-positive amount:",
                    raw_numeric_amount,
                )

                return finish(result)

        else:
            print("DEBUG: Gemini returned no usable intent.")

        if (
            isinstance(llm_result, dict)
            and llm_result.get("intent") == "payment_request"
        ):
            amount_phrase = normalize_llm_amount(
                llm_result.get("amount_text")
            )

            payee_value = llm_result.get("payee_name")
            matched_payee = normalize_llm_payee(payee_value)

            # Reject recipients that are not registered.
            if payee_value and not matched_payee:
                state.payee_name = None
                state.amount_text = (
                    f"{amount_phrase} rupees"
                    if amount_phrase
                    else None
                )

                result = {
                    "status": "needs_clarification",
                    "message": (
                        "I couldn't match that recipient to a registered "
                        "payee. Please choose a registered recipient."
                    ),
                    "registered_payees": [
                        payee.name for payee in MOCK_PAYEES
                    ],
                }

                print("DEBUG Gemini recipient not registered.")
                return finish(result)

            if matched_payee and not amount_phrase:
                result = handle_payment_turn(
                    state,
                    payee_name=matched_payee.name,
                )

                print("DEBUG Gemini recipient:", matched_payee.name)
                return finish(result)

            if amount_phrase and not matched_payee:
                state.payee_name = None
                state.amount_text = f"{amount_phrase} rupees"

                result = handle_payment_turn(state)

                print("DEBUG Gemini amount:", amount_phrase)
                return finish(result)

            if amount_phrase and matched_payee:
                result = handle_payment_turn(
                    state,
                    payee_name=matched_payee.name,
                    amount_text=f"{amount_phrase} rupees",
                )

                print(
                    "DEBUG Gemini payment request:",
                    repr(
                        {
                            "amount": amount_phrase,
                            "payee": matched_payee.name,
                        }
                    ),
                )

                return finish(result)

        # Handle other intents without creating a payment.
        if (
            isinstance(llm_result, dict)
            and llm_result.get("intent") in {
                "confirmation",
                "cancellation",
            }
        ):
            result = {
                "status": "needs_clarification",
                "message": (
                    "There is no pending payment to confirm or cancel."
                ),
            }

            print(
                "DEBUG no pending payment for confirmation/cancellation."
            )

            return finish(result)

        result = {
            "status": "needs_clarification",
            "message": (
                "Please say: Pay [amount] rupees to [registered payee]. "
                "You can also speak in Hindi."
            ),
            "registered_payees": [
                payee.name for payee in MOCK_PAYEES
            ],
        }

        print("DEBUG: Speech did not match a payment request.")
        return finish(result)

    except ValueError as exc:
        print("DEBUG validation error:", repr(str(exc)))

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    finally:
        await file.close()

        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
