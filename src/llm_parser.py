"""
LLM Parser Module

- Uses an LLM ONLY to convert raw OCR text -> structured JSON matching ParsedDeed schema.
- Does NOT validate correctness (dates/money), that happens in validators.py.
- Supports OpenAI OR a free LLM API OR an offline stub fallback.
"""

import json
import os
import re
from typing import Any, Dict

import requests
from dotenv import load_dotenv
from pydantic import ValidationError

from src.exceptions import LLMParseError
from src.models import ParsedDeed

# Load .env from project root
load_dotenv()

# -----------------------
# Config / Toggles (from .env)
# -----------------------

def _env_bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name, str(default)).strip().lower()
    return val in {"1", "true", "yes", "y", "on"}

USE_OPENAI = _env_bool("USE_OPENAI", False)
FREE_LLM_URL = os.getenv("FREE_LLM_URL", "https://apifreellm.com/api/v1/chat").strip()

RAW_DEED_TEXT = """*** RECORDING REQ ***
Doc: DEED-TRUST-0042
County: S. Clara | State: CA
Date Signed: 2024-01-15
Date Recorded: 2024-01-10
Grantor: T.E.S.L.A. Holdings LLC
Grantee: John & Sarah Connor
Amount: $1,250,000.00 (One Million Two Hundred Thousand Dollars)
APN: 992-001-XA
Status: PRELIMINARY
*** END ***"""

SYSTEM_PROMPT = (
    "You extract structured data from legal documents.\n"
    "You do NOT fix errors.\n"
    "You do NOT infer missing values.\n"
    "You ONLY return valid JSON that matches the provided schema.\n"
)

USER_PROMPT = """
Extract the following deed text into a JSON object with these exact fields:

document_type
document_id
county_raw
state
date_signed (YYYY-MM-DD)
date_recorded (YYYY-MM-DD)
grantor
grantee (array of full names)
amount_numeric (number, no currency symbols)
amount_text
apn
status

Return ONLY JSON (no explanation, no markdown) if possible.

Text:
{raw_text}
""".strip()


# -----------------------
# Helpers
# -----------------------

def _strip_code_fences(text: str) -> str:
    if not text:
        return text
    t = text.strip()
    m = re.match(r"^```(?:json)?\s*(.*?)\s*```$", t, flags=re.DOTALL | re.IGNORECASE)
    return m.group(1).strip() if m else t


def _call_stub_llm() -> str:
    return json.dumps(
        {
            "document_type": "DEED-TRUST",
            "document_id": "DEED-TRUST-0042",
            "county_raw": "S. Clara",
            "state": "CA",
            "date_signed": "2024-01-15",
            "date_recorded": "2024-01-10",
            "grantor": "T.E.S.L.A. Holdings LLC",
            "grantee": ["John Connor", "Sarah Connor"],
            "amount_numeric": 1250000,
            "amount_text": "One Million Two Hundred Thousand Dollars",
            "apn": "992-001-XA",
            "status": "PRELIMINARY",
        }
    )


# -----------------------
# Provider calls
# -----------------------

def _call_openai(prompt: str) -> str:
    try:
        from openai import OpenAI
    except Exception as exc:
        raise LLMParseError("openai package not installed. Install it or set USE_OPENAI=false.") from exc

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise LLMParseError("Missing OPENAI_API_KEY. Set it or set USE_OPENAI=false.")

    client = OpenAI(api_key=api_key)

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
        )
        return resp.choices[0].message.content
    except Exception as exc:
        raise LLMParseError(f"OpenAI request failed: {exc}") from exc


def _call_free_llm(prompt: str) -> str:
    api_key = os.getenv("FREE_LLM_API_KEY")

    # No key → use stub (dev-friendly)
    if not api_key:
        return _call_stub_llm()

    r = requests.post(
        FREE_LLM_URL,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        json={"message": prompt},
        timeout=60,
    )

    # Invalid key → stub (or raise, but stub keeps dev running)
    if r.status_code == 401:
        return _call_stub_llm()

    if r.status_code != 200:
        raise LLMParseError(f"Free LLM request failed with status {r.status_code}: {r.text}")

    data: Dict[str, Any] = r.json()

    if data.get("success") is not True:
        raise LLMParseError(f"Free LLM returned success!=True: {data}")

    content = data.get("response")
    if not isinstance(content, str) or not content.strip():
        raise LLMParseError(f"Free LLM missing/invalid 'response' field: {data}")

    return _strip_code_fences(content)


# -----------------------
# Public function
# -----------------------

def parse_deed_with_llm(raw_text: str = RAW_DEED_TEXT) -> ParsedDeed:
    prompt = USER_PROMPT.format(raw_text=raw_text)

    content = _call_openai(prompt) if USE_OPENAI else _call_free_llm(prompt)
    content = _strip_code_fences(content)

    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise LLMParseError(f"LLM did not return valid JSON. Raw content: {content}") from exc

    try:
        return ParsedDeed.model_validate(data)
    except ValidationError as exc:
        raise LLMParseError(f"LLM output failed schema validation: {exc}") from exc
