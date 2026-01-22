import sys
from pathlib import Path

# Make src/ importable
ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"
sys.path.append(str(SRC_DIR))

from src.enrich import enrich_deed
from src.exceptions import BadDeedError
from src.llm_parser import parse_deed_with_llm
from src.validators import run_all_validations


def main() -> None:
    try:
        # 1. Parse raw OCR text using LLM
        parsed_deed = parse_deed_with_llm()

        # 2. Run deterministic sanity checks
        run_all_validations(parsed_deed)

        # 3. Enrich with reference data (county + tax rate)
        enriched_deed = enrich_deed(parsed_deed)

        print("✅ Deed accepted")
        print(enriched_deed.model_dump())

    except BadDeedError as exc:
        print("❌ Deed rejected")
        print(f"Reason: {exc}")

    except Exception as exc:
        # Anything else is a true system failure
        print("🔥 Unexpected system error")
        raise exc


if __name__ == "__main__":
    main()
