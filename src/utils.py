import re
from decimal import Decimal

from word2number import w2n


def normalize_text(text: str) -> str:
    """
    Basic text normalization for matching/comparison.
    """
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)   # remove punctuation
    text = re.sub(r"\s+", " ", text)       # collapse spaces
    return text.strip()


def money_text_to_decimal(text_amount: str) -> Decimal:
    """
    Convert text money representation into Decimal.

    Example:
        "One Million Two Hundred Thousand Dollars" -> Decimal("1200000")
    """
    normalized = normalize_text(text_amount)

    # remove currency words
    normalized = normalized.replace("dollars", "").replace("dollar", "").strip()

    value = w2n.word_to_num(normalized)
    return Decimal(value)
