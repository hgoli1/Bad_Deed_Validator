from decimal import Decimal
import re

from src.exceptions import InvalidDateOrderError, AmountMismatchError
from src.models import ParsedDeed


def validate_date_order(deed: ParsedDeed) -> None:
    """
    Ensure the document was signed before or on the date it was recorded.
    """
    if deed.date_recorded < deed.date_signed:
        raise InvalidDateOrderError(
            signed_date=deed.date_signed,
            recorded_date=deed.date_recorded,
        )


# --- Robust text money parser (deterministic, no LLM, no flaky libs) ---

_NUM_WORDS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}

_SCALES = {
    "hundred": 100,
    "thousand": 1_000,
    "million": 1_000_000,
    "billion": 1_000_000_000,
}


def _words_to_int(text: str) -> int:
    """
    Convert English number words into an integer.
    Handles: hundred, thousand, million, billion.
    Example: "one million two hundred thousand" -> 1200000
    """
    # Normalize: lowercase, remove punctuation, handle hyphens, remove currency words
    cleaned = text.lower()
    cleaned = cleaned.replace("-", " ")
    cleaned = re.sub(r"[^\w\s]", " ", cleaned)  # remove punctuation
    tokens = [t for t in cleaned.split() if t not in {"and", "dollar", "dollars"}]

    if not tokens:
        raise ValueError("No tokens to parse")

    total = 0
    current = 0

    for token in tokens:
        if token in _NUM_WORDS:
            current += _NUM_WORDS[token]

        elif token == "hundred":
            if current == 0:
                current = 1
            current *= _SCALES[token]

        elif token in ("thousand", "million", "billion"):
            scale = _SCALES[token]
            if current == 0:
                current = 1
            total += current * scale
            current = 0

        else:
            # Unknown token (e.g., "usd") -> ignore or fail
            # For this task, safest is to FAIL so we don't accept bad parsing.
            raise ValueError(f"Unknown number token: {token}")

    return total + current


def _text_amount_to_decimal(text_amount: str) -> Decimal:
    """
    Convert textual money representation into a Decimal.
    Example:
        "One Million Two Hundred Thousand Dollars" -> Decimal("1200000")
    """
    try:
        value = _words_to_int(text_amount)
        return Decimal(value)
    except Exception as exc:
        raise AmountMismatchError(
            numeric_amount="unknown",
            textual_amount=text_amount,
        ) from exc


def validate_amount_consistency(deed: ParsedDeed) -> None:
    """
    Ensure numeric and textual monetary amounts match exactly.
    """
    textual_amount = _text_amount_to_decimal(deed.amount_text)

    # deed.amount_numeric is Decimal (from pydantic); ensure comparable
    numeric_amount = Decimal(deed.amount_numeric)

    if numeric_amount != textual_amount:
        raise AmountMismatchError(
            numeric_amount=numeric_amount,
            textual_amount=textual_amount,
        )


def run_all_validations(deed: ParsedDeed) -> None:
    """
    Run all deterministic sanity checks.
    """
    validate_date_order(deed)
    validate_amount_consistency(deed)
