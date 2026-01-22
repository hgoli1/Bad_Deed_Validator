import json
import re
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from rapidfuzz import process, fuzz

from src.exceptions import UnknownCountyError
from src.models import ParsedDeed, EnrichedDeed


DATA_DIR = Path("data")
COUNTIES_FILE = DATA_DIR / "counties.json"

# Token scorers are more robust for OCR variations
MATCH_THRESHOLD = 70

_ABBREV_MAP = {
    "s": "santa",
    "s.": "santa",
    "st": "saint",
    "st.": "saint",
}


def _load_counties() -> List[Dict]:
    if not COUNTIES_FILE.exists():
        raise FileNotFoundError(f"Missing counties file: {COUNTIES_FILE}")

    with open(COUNTIES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _normalize_county_name(name: str) -> str:
    """
    Robust county normalization for OCR noise.

    Handles:
    - "S.Clara" -> "santa clara"
    - "Santa Clara County" -> "santa clara"
    - punctuation/hyphens/extra separators
    - St./S. abbreviation expansion (first token)
    """
    if not name:
        return ""

    text = name.strip().lower()

    # 1) Insert spaces where OCR glues tokens around punctuation:
    #    "S.Clara" -> "S. Clara", "SanLuis" not handled (needs fuzzy)
    text = re.sub(r"([a-zA-Z])\.", r"\1. ", text)      # letter-dot -> letter-dot-space
    text = re.sub(r"\s+", " ", text)                   # collapse whitespace

    # 2) Replace separators with spaces
    text = text.replace("-", " ")
    text = text.replace("/", " ")
    text = text.replace(",", " ")
    text = text.replace("|", " ")

    # 3) Remove remaining punctuation (keep word characters + space)
    text = re.sub(r"[^\w\s\.]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    # 4) Tokenize and remove filler words
    tokens = [t for t in text.split() if t not in {"county", "of", "the"}]

    if not tokens:
        return ""

    # 5) Expand abbreviations on first token
    first = tokens[0]
    if first in _ABBREV_MAP:
        tokens[0] = _ABBREV_MAP[first]

    # 6) Remove dots in tokens after expansion (st. -> saint)
    tokens = [t.replace(".", "") for t in tokens]

    return " ".join(tokens).strip()


def enrich_deed(deed: ParsedDeed) -> EnrichedDeed:
    counties = _load_counties()
    county_names = [c["name"] for c in counties]

    match: Optional[Tuple[str, float, int]] = process.extractOne(
        deed.county_raw,
        county_names,
        processor=_normalize_county_name,
        scorer=fuzz.token_set_ratio,
    )

    if not match:
        raise UnknownCountyError(f"Unable to match county '{deed.county_raw}'")

    matched_name, score, _ = match

    if score < MATCH_THRESHOLD:
        raise UnknownCountyError(
            f"Unable to confidently match county '{deed.county_raw}' "
            f"(best='{matched_name}', score={score})"
        )

    county_record = next(c for c in counties if c["name"] == matched_name)

    return EnrichedDeed(
        **deed.model_dump(),
        county_canonical=county_record["name"],
        tax_rate=Decimal(str(county_record["tax_rate"])),
    )
