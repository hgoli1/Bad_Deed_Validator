# Bad Deed Validator

A Python application that validates real estate deed documents by parsing OCR text, extracting structured data using LLMs, and performing deterministic validation checks.

## Overview

The Bad Deed Validator processes raw deed documents through three stages:

1. **LLM Parsing** - Converts raw OCR text to structured JSON matching a defined schema
2. **Validation** - Performs deterministic sanity checks (date order, amount consistency)
3. **Enrichment** - Matches counties to reference data and attaches tax rates

## Features

- **LLM Provider Toggle** - Switch between OpenAI and free LLM API via `USE_OPENAI` flag
- **Robust Parsing** - Handles OCR noise and variations in deed text
- **Deterministic Validation** - Date order and monetary amount consistency checks
- **County Matching** - Fuzzy matching with abbreviation expansion (S. Clara → Santa Clara)
- **Tax Rate Enrichment** - Attaches canonical county names and tax rates from reference data
- **Fallback Support** - Uses offline stub when API key is missing or invalid

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
