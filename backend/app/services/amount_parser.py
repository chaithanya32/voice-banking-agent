
import re
from decimal import Decimal, InvalidOperation


NUMBER_WORDS = {
    "zero": 0,
    "ek": 1,
    "one": 1,
    "do": 2,
    "two": 2,
    "teen": 3,
    "tin": 3,
    "three": 3,
    "char": 4,
    "chaar": 4,
    "four": 4,
    "paanch": 5,
    "panch": 5,
    "five": 5,
    "chhe": 6,
    "che": 6,
    "six": 6,
    "saat": 7,
    "seven": 7,
    "aath": 8,
    "eight": 8,
    "nau": 9,
    "nine": 9,
    "das": 10,
    "ten": 10,
    "gyarah": 11,
    "barah": 12,
    "terah": 13,
    "chaudah": 14,
    "pandrah": 15,
    "solah": 16,
    "satrah": 17,
    "atharah": 18,
    "unnis": 19,
    "bees": 20,
    "tees": 30,
    "chalis": 40,
    "pachaas": 50,
    "saath": 60,
    "sattar": 70,
    "assi": 80,
    "nabbe": 90,
}

SCALES = {
    "sau": 100,
    "hundred": 100,
    "hazaar": 1_000,
    "hazar": 1_000,
    "thousand": 1_000,
    "lakh": 100_000,
    "lac": 100_000,
    "lakhs": 100_000,
}


def parse_amount(text: str) -> Decimal:
    """Parse supported numeric and Hinglish rupee amounts."""

    if not isinstance(text, str) or not text.strip():
        raise ValueError("Amount is required.")

    normalized = text.lower().strip()

    # Remove supported currency labels without changing number separators.
    normalized = re.sub(
        r"\brs\.?\b|₹|rupees?|rupaye|rupya",
        " ",
        normalized,
    )
    normalized = re.sub(r"\s+", " ", normalized).strip()

    # Reject negative amounts.
    if re.search(r"(?<!\w)-\s*\d", normalized):
        raise ValueError("Negative amounts are not allowed.")

    # Accept valid numeric formats:
    # 500, 1500, 1,500, 10,000, 10,000.50
    numeric_input = re.fullmatch(
        r"-?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d{1,2})?",
        normalized,
    )

    if numeric_input:
        try:
            amount = Decimal(normalized.replace(",", ""))
        except InvalidOperation as exc:
            raise ValueError("Invalid amount.") from exc

        if amount <= 0:
            raise ValueError("Amount must be positive.")

        return amount

    # Reject numeric amounts mixed with other text or malformed commas.
    numeric_matches = re.findall(
        r"(?<![\w.])-?\d+(?:\.\d{1,2})?(?![\w.])",
        normalized,
    )

    if numeric_matches:
        raise ValueError(
            "Ambiguous input: provide only the amount, without other text."
        )

    # Special fractional Hindi number phrases.
    special_phrases = {
        "dedh hazaar": Decimal("1500"),
        "dedh lakh": Decimal("150000"),
        "dhai sau": Decimal("250"),
        "dhai hazaar": Decimal("2500"),
        "sawa sau": Decimal("125"),
        "sawa do lakh": Decimal("225000"),
        "sawa lakh": Decimal("125000"),
        "paune do hazaar": Decimal("1750"),
    }

    if normalized in special_phrases:
        return special_phrases[normalized]

    tokens = normalized.split()

    if not tokens or any(
        token not in NUMBER_WORDS and token not in SCALES
        for token in tokens
    ):
        raise ValueError("Unsupported or ambiguous amount phrase.")

    total = 0
    current = 0

    for token in tokens:
        if token in NUMBER_WORDS:
            current += NUMBER_WORDS[token]

        elif token in SCALES:
            scale = SCALES[token]

            if current == 0:
                raise ValueError("Amount phrase is incomplete.")

            if scale == 100:
                current *= scale
            else:
                total += current * scale
                current = 0

    amount = Decimal(total + current)

    if amount <= 0:
        raise ValueError("Amount must be positive.")

    return amount
