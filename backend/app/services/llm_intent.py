
import json
import os
from typing import Optional

from dotenv import load_dotenv
from google import genai


load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

client = genai.Client(api_key=API_KEY) if API_KEY else None


def interpret_payment_intent(spoken_text: str) -> Optional[dict]:
    """
    Interpret a user's payment-related message.

    This function only extracts intent. It never creates,
    confirms, cancels, or executes a payment.
    """
    text = spoken_text.strip()

    if not text or client is None:
        return None

    prompt = f"""
Rules:
1. Understand English, Hindi, and common Hinglish.
2. Convert clearly spoken amounts into numeric rupees.
   Example: "पाँच सौ रुपये" becomes "500".
3. The only registered recipients are:
   - Ravi Kumar
   - Priya Sharma
   - Rahul Reddy
4. Match a recipient to one of these names only when the
   user's message clearly identifies that person.
   Example: "रवि" may match "Ravi Kumar".
5. If the amount or recipient is unclear, return null
   for that field. Never guess.
6. "Yes", "haan", and "confirm" can indicate confirmation.
7. "No", "nahi", and "cancel" can indicate cancellation.
8. A balance or transaction-history question is "other".
9. Return only the requested JSON object.
10. Interpretation is not authorization to transfer money.
User message:
{text}
"""

    try:
        response = client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": {
                    "type": "OBJECT",
                    "properties": {
                        "intent": {
                            "type": "STRING",
                            "enum": [
                                "payment_request",
                                "confirmation",
                                "cancellation",
                                "other",
                            ],
                        },
                        "amount_text": {
                        "type": "STRING",
                        "nullable": True,
                    },
                    "payee_name": {
                        "type": "STRING",
                        "nullable": True,
                    },
                    },
                    "required": [
                        "intent",
                        "amount_text",
                        "payee_name",
                    ],
                },
            },
        )

        result = json.loads(response.text)

        if not isinstance(result, dict):
            return None

        if result.get("intent") not in {
            "payment_request",
            "confirmation",
            "cancellation",
            "other",
        }:
            return None

        amount = result.get("amount_text")
        payee = result.get("payee_name")

        if amount is not None and not isinstance(amount, str):
            return None

        if payee is not None and not isinstance(payee, str):
            return None

        return {
            "intent": result["intent"],
            "amount_text": amount,
            "payee_name": payee,
        }

    except Exception as exc:
        # Keep the existing deterministic parser available if
        # the model, network, or response fails.
        print("Gemini intent interpretation failed:", str(exc))
        return None
