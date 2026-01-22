# Bad Deed Validator

A paranoid, production-minded approach to validating OCR-scanned legal deeds using an LLM without trusting it for correctness.

**Core Philosophy:** Use AI to extract structure from messy text. Use deterministic code to decide whether the data is acceptable.

At no point is the LLM allowed to silently fix, infer, or approve anything.

## Problem Summary

Given:

- Messy OCR text from a deed
- A local reference file (`counties.json`) with tax rates

We need to:

- Parse the OCR text into structured data
- Normalize and enrich reference fields (county → tax rate)
- Perform strict sanity checks that must fail loudly if the data is inconsistent

Two specific failure cases are intentionally present:

1. The deed is recorded before it is signed
2. The numeric and written amounts do not match

Both must be caught by code, not AI.

## High-Level Architecture

```
Raw OCR Text
     ↓
LLM Parser (fuzzy, non-authoritative)
     ↓
Pydantic Models (schema enforcement)
     ↓
Deterministic Validators (dates, money)
     ↓
Deterministic Enricher (county → tax rate)
     ↓
Accept or Reject
```

**Key principle:** AI suggests. Code decides.

## Why the LLM Is Constrained

The LLM is used only for:

- Extracting fields from unstructured text
- Normalizing formatting
- Producing structured JSON

The LLM is explicitly instructed to:

- NOT fix errors
- NOT infer missing data
- NOT reconcile inconsistencies

All correctness decisions are enforced by:

- **Pydantic schema validation** - Catches malformed data immediately
- **Deterministic Python logic** - Makes all business decisions

If the LLM output is malformed or incomplete, the pipeline fails immediately.

## Validation Strategy

### 1. Date Sanity Check

The recorded date must not be earlier than the signed date.

```
Validation Rule: date_recorded >= date_signed
```

This is enforced using deterministic datetime comparisons. If violated, the deed is rejected with a clear error message.

### 2. Monetary Consistency Check

The numeric amount and the written amount must match exactly.

```
Validation Rule: amount_numeric == text_to_number(amount_text)
```

The written amount is converted to a number using deterministic code (`word2number`), not AI. Any discrepancy results in immediate rejection.

**No silent corrections. No heuristics.**

### 3. County Enrichment & Matching

OCR text contains abbreviated or inconsistent county names (e.g., "S. Clara", "ST.CLARA", etc.).

The system:

- Normalizes strings deterministically (handles punctuation, abbreviations like "S." → "Santa", "St." → "Saint")
- Uses fuzzy matching (via `rapidfuzz`) against `counties.json`
- Enforces a confidence threshold (70% match score)
- If a county cannot be confidently matched, the deed is rejected

Examples:

- "S. Clara" → matches "Santa Clara" (normalized + fuzzy match)
- "Santa Clara County" → matches "Santa Clara" (removes filler words)
- "Unknown County" → **REJECTED** (no confident match)

## Project Structure

```
.
├── main.py                 # Entry point
├── requirements.txt        # Python dependencies
├── .env                    # Environment configuration (not committed)
├── .gitignore             # Git ignore rules
├── README.md              # This file
├── data/
│   └── counties.json      # County reference data
└── src/
    ├── __pycache__/       # Python cache
    ├── models.py          # Pydantic models (ParsedDeed, EnrichedDeed)
    ├── llm_parser.py      # LLM integration and deed parsing
    ├── validators.py      # Deterministic validation logic
    ├── enrich.py          # County matching and enrichment
    ├── utils.py           # Utility functions
    └── exceptions.py      # Custom exception classes
```

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Edit `.env` to choose your LLM provider:

**For OpenAI (set `USE_OPENAI=true`):**

```dotenv
USE_OPENAI=true
OPENAI_API_KEY=sk-your-openai-api-key-here
```

**For Free LLM (set `USE_OPENAI=false`):**

```dotenv
USE_OPENAI=false
FREE_LLM_API_KEY=your_free_llm_api_key_here
FREE_LLM_URL=https://apifreellm.com/api/v1/chat
```

If `FREE_LLM_API_KEY` is missing or returns 401 (unauthorized), the app falls back to a stub LLM for development.

## Usage

### Run the Application

```bash
python main.py
```

### Expected Output

On success:

```
✅ Deed accepted
{
  "document_type": "DEED-TRUST",
  "document_id": "DEED-TRUST-0042",
  ...
  "county_canonical": "Santa Clara",
  "tax_rate": "1.25"
}
```

On validation failure:

```
❌ Deed rejected
Reason: Invalid date order: recorded date (2024-01-10) is earlier than signed date (2024-01-15)
```

## Architecture

### Models (`src/models.py`)

- **ParsedDeed** - LLM output with raw county name
- **EnrichedDeed** - ParsedDeed + canonical county name + tax rate

### LLM Parser (`src/llm_parser.py`)

Supports provider switching via `LLM_PROVIDER` environment variable:

- **openai** - Uses OpenAI API with OpenAI client
- **apifreellm** - Uses apifreellm.com with OpenAI client (compatible base URL)

### Validators (`src/validators.py`)

- `validate_date_order()` - Checks signed date ≤ recorded date
- `validate_amount_consistency()` - Ensures numeric and textual amounts match
- `run_all_validations()` - Orchestrates all checks

### Enrictwo LLM providers via `USE_OPENAI` toggle in `.env`:

- **OpenAI** (`USE_OPENAI=true`) - Uses OpenAI API. Requires `OPENAI_API_KEY`
- **Free LLM** (`USE_OPENAI=false`) - Uses apifreellm.com API. Requires `FREE_LLM_API_KEY`
  - Falls back to offline stub if key is missing or invalid (401)
  - Strips markdown code fences from responses
- Attaches tax rates from reference data

## Configuration Reference

### Environment Variables

| Variable             | Required            | Default            | Description                            |
| -------------------- | ------------------- | ------------------ | -------------------------------------- |
| `LLM_PROVIDER`       | No                  | openai             | LLM provider: "openai" or "apifreellm" |
| `OPENAI_API_KEY`     | Yes (if openai)     | -                  | OpenAI API key                         |
| `APIFREELLM_API_KEY` | Yes (if apifreellm) | -                  | apifreellm.com API key                 |
| `LLM_MODEL`          | No                  | (provider default) | Model name override                    |
| `LLM_BASE_URL`       | No                  | (provider default) | Custom API endpoint                    |
| `DEBUG`              | No                  | false              | Enable debug mode                      |
| `LOG_LEVEL`          | No                  | INFO               | Logging level                          |

## Example Deed Text

The application includes a sample deed for testing:

```
*** RECORDING REQ ***
Doc: DEED-TRUST-0042
County: S. Clara | State: CA
Date Signed: 2024-01-15
Date Recorded: 2024-01-10
Grantor: T.E.S.L.A. Holdings LLC
Grantee: John & Sarah Connor
Amount: $1,250,000.00 (One Million Two Hundred Thousand Dollars)
APN: 992-001-XA
Status: PRELIMINARY
*** END ***
```

## Error Handling

Exceptions inherit from `BadDeedError`:

- **LLMParseError** - LLM failed to return valid JSON or schema validation failed
- **InvalidDateOrderError** - Recorded date before signed date
- **AmountMismatchError** - Numeric and textual amounts don't match
- **UnknownCountyError** - County name couldn't be matched to reference data

## Development

### Running Tests

```bash
pytest
```

### Linting

```bash
pylint src/
```

### Code Formatting

```bash
black src/
```

## Dependencies

- `openai` - OpenAI SDK (compatible with apifreellm.com)
- `pydantic` - Data validation
- `rapidfuzz` - Fuzzy string matching
- `python-dotenv` - Environment variable loading
- `requests` - HTTP library
- `word2number` - Text-to-number conversion

## License

[Add license information]

## Notes

- The LLM is only responsible for schema correctness, not logical correctness
- Logical validation (dates, amounts) is performed deterministically in `validators.py`
- Fallback to stub LLM available for development without API keys
