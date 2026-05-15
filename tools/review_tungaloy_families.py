import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.review_catalog_records import (  # noqa: E402
    load_staged_records,
    mark_record_reviewed,
    save_reviewed_records,
    validate_reviewed_record,
)


INPUT_PATH = REPO_ROOT / "tool_data" / "catalog_ingestion" / "staged" / "tungaloy_multifunction_families.json"
OUTPUT_FILENAME = "tungaloy_multifunction_families.json"
REVIEWER = "Joshua Hayes"
REVIEW_NOTES = (
    "Reviewed as family-level guidance only for grooving, threading, high-feed, and multifunction tooling systems. "
    "Exact insert forms, grades, cutter platforms, holder details, catalog numbers, and cutting data must still "
    "be verified from the manufacturer catalog before production use."
)


def build_reviewed_tungaloy_records() -> list[dict]:
    return [
        mark_record_reviewed(record, reviewer=REVIEWER, notes=REVIEW_NOTES)
        for record in load_staged_records(INPUT_PATH)
    ]


def review_tungaloy_family_records() -> Path:
    records = build_reviewed_tungaloy_records()
    errors: list[str] = []
    for index, record in enumerate(records):
        errors.extend(f"record {index}: {error}" for error in validate_reviewed_record(record))
    if errors:
        raise ValueError("; ".join(errors))
    return save_reviewed_records(
        "tungaloy",
        records,
        output_filename=OUTPUT_FILENAME,
    )


if __name__ == "__main__":
    output_path = review_tungaloy_family_records()
    print(f"Saved {len(build_reviewed_tungaloy_records())} reviewed Tungaloy family records to {output_path}.")
