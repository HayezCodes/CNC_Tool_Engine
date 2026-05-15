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


INPUT_PATH = REPO_ROOT / "tool_data" / "catalog_ingestion" / "staged" / "niagara_cutter_milling_families.json"
OUTPUT_FILENAME = "niagara_cutter_milling_families.json"
REVIEWER = "Joshua Hayes"
REVIEW_NOTES = (
    "Reviewed as family-level guidance only for Niagara Cutter production milling families. "
    "Exact geometry, dimensions, coatings, catalog numbers, and cutting data must still be verified from the "
    "manufacturer catalog or official brand references before production use."
)


def build_reviewed_niagara_cutter_records() -> list[dict]:
    return [
        mark_record_reviewed(record, reviewer=REVIEWER, notes=REVIEW_NOTES)
        for record in load_staged_records(INPUT_PATH)
    ]


def review_niagara_cutter_family_records() -> Path:
    records = build_reviewed_niagara_cutter_records()
    errors: list[str] = []
    for index, record in enumerate(records):
        errors.extend(f"record {index}: {error}" for error in validate_reviewed_record(record))
    if errors:
        raise ValueError("; ".join(errors))
    return save_reviewed_records(
        "niagara_cutter",
        records,
        output_filename=OUTPUT_FILENAME,
    )


if __name__ == "__main__":
    output_path = review_niagara_cutter_family_records()
    print(f"Saved {len(build_reviewed_niagara_cutter_records())} reviewed Niagara Cutter family records to {output_path}.")
