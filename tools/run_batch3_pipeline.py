"""Run the full parse/import/review pipeline for Batch 3 manufacturers.

Batch 3: YG-1, Helical Solutions, Harvey Tool.

Usage:
    python tools/run_batch3_pipeline.py
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools.tooling_adapters.yg1_adapter import parse_yg1_file
from tools.tooling_adapters.helical_solutions_adapter import parse_helical_solutions_file
from tools.tooling_adapters.harvey_tool_adapter import parse_harvey_tool_file
from tools.import_tooling_records import import_tooling_records
from tools.review_tooling_records import batch_review_records, save_reviewed_tooling_records
from grade_engine.tooling_search import RECORDS_DIR

SAMPLES_DIR = _REPO_ROOT / "tools" / "tooling_adapters" / "samples"
OUTPUT_DIR = _REPO_ROOT / "tools" / "tooling_adapters" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

REVIEW_NOTES = (
    "Synthetic adapter fixture reviewed only to prove the import/audit/review/search pipeline. "
    "Not manufacturer catalog data."
)
REVIEWER = "Joshua Hayes"
REVIEW_DATE = date.today().isoformat()

MANUFACTURERS = [
    {
        "brand": "YG-1",
        "parse_fn": parse_yg1_file,
        "fixture": SAMPLES_DIR / "sample_yg1_structured.json",
        "output": OUTPUT_DIR / "yg1_sample_records.json",
        "imported": RECORDS_DIR / "yg1_imported_tools.json",
        "reviewed_slug": "yg-1",
    },
    {
        "brand": "Helical Solutions",
        "parse_fn": parse_helical_solutions_file,
        "fixture": SAMPLES_DIR / "sample_helical_solutions_structured.json",
        "output": OUTPUT_DIR / "helical_solutions_sample_records.json",
        "imported": RECORDS_DIR / "helical_solutions_imported_tools.json",
        "reviewed_slug": "helical-solutions",
    },
    {
        "brand": "Harvey Tool",
        "parse_fn": parse_harvey_tool_file,
        "fixture": SAMPLES_DIR / "sample_harvey_tool_structured.json",
        "output": OUTPUT_DIR / "harvey_tool_sample_records.json",
        "imported": RECORDS_DIR / "harvey_tool_imported_tools.json",
        "reviewed_slug": "harvey-tool",
    },
]


def run_manufacturer(cfg: dict) -> bool:
    brand = cfg["brand"]
    print(f"\n{'='*60}")
    print(f"  {brand}")
    print(f"{'='*60}")

    # 1. Parse
    print(f"[1] Parsing {cfg['fixture'].name} ...")
    result = cfg["parse_fn"](cfg["fixture"])
    if result["parse_errors"] or result["validation_errors"]:
        print(f"    ERRORS: {result['parse_errors'] + result['validation_errors']}")
        return False
    print(f"    OK — {result['record_count']} records, {result['rejected_count']} rejected")

    # 2. Write adapter output
    cfg["output"].write_text(json.dumps(result["records"], indent=2) + "\n", encoding="utf-8")
    print(f"[2] Adapter output -> {cfg['output'].name}")

    # 3. Import
    print(f"[3] Importing to {cfg['imported'].name} ...")
    imp = import_tooling_records(cfg["output"], output_path=cfg["imported"], dry_run=False)
    if imp["errors"]:
        print(f"    IMPORT ERRORS: {imp['errors']}")
        return False
    print(f"    OK — {imp['normalized_record_count']} records written")

    # 4. Review
    print(f"[4] Reviewing {cfg['imported'].name} ...")
    imported_records = json.loads(cfg["imported"].read_text(encoding="utf-8"))
    promoted, errors = batch_review_records(
        imported_records,
        review_status="reviewed_family_level_candidate",
        reviewer=REVIEWER,
        review_date=REVIEW_DATE,
        review_notes=REVIEW_NOTES,
    )
    if errors:
        print(f"    REVIEW ERRORS: {errors}")
        return False
    reviewed_path = save_reviewed_tooling_records(cfg["reviewed_slug"], promoted)
    print(f"    OK — {len(promoted)} records reviewed -> {reviewed_path.name}")

    return True


def main() -> int:
    all_ok = True
    for cfg in MANUFACTURERS:
        if not run_manufacturer(cfg):
            all_ok = False
    print(f"\n{'='*60}")
    print(f"  Batch 3 pipeline {'COMPLETE' if all_ok else 'FAILED'}")
    print(f"{'='*60}\n")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
