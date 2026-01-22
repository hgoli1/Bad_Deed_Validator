from datetime import date
from decimal import Decimal
from typing import List

from pydantic import BaseModel, Field, ValidationError


class ParsedDeed(BaseModel):
    """
    Canonical structured output expected from the LLM.
    This model represents parsed data only — no enrichment, no validation.
    """

    document_type: str = Field(..., description="Type of document, e.g. DEED-TRUST")
    document_id: str = Field(..., description="Document identifier")
    county_raw: str = Field(..., description="County name as written in the deed")
    state: str = Field(..., min_length=2, max_length=2)
    date_signed: date
    date_recorded: date

    grantor: str
    grantee: List[str]

    amount_numeric: Decimal = Field(..., gt=0)
    amount_text: str

    apn: str
    status: str


class EnrichedDeed(ParsedDeed):
    """
    Parsed deed + reference data enrichment.
    """

    county_canonical: str
    tax_rate: Decimal
