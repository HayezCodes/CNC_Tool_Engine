from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from grade_engine.tooling_search import RECORDS_DIR, normalize_tool_query


REVIEWED_DIR = RECORDS_DIR / "reviewed"

ALLOWED_REVIEW_STATUSES = frozenset({
    "reviewed_exact_tool_candidate",
    "reviewed_family_level_candidate",
})

_FORBIDDEN_FIELD_TERMS = ("feed", "speed", "sfm", "rpm", "ipr", "ipm", "vc", "fz")


def _field_contains_forbidden_term(field_name: str) -> bool:
    lowered = normalize_tool_query(str(field_name))
    return any(term in lowered for term in _FORBIDDEN_FIELD_TERMS)


def load_tooling_records_for_review(path: str | Path) -> list[dict[str, Any]]:
    path = Path(path)
    records = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise ValueError(f"Records file must contain a JSON array: {path}")
    return records


def validate_record_for_review(record: dict[str, Any], review_status: str) -> list[str]:
    errors: list[str] = []

    # Reject records with forbidden feed/speed fields
    forbidden = sorted(f for f in record if _field_contains_forbidden_term(str(f)))
    if forbidden:
        errors.append(f"Contains forbidden feed/speed fields: {', '.join(forbidden)}")

    # Validate review status
    if review_status not in ALLOWED_REVIEW_STATUSES:
        errors.append(
            f"review_status '{review_status}' is not allowed. "
            f"Must be one of: {sorted(ALLOWED_REVIEW_STATUSES)}"
        )

    # Source traceability required
    if not str(record.get("source_label", "")).strip():
        errors.append("source_label is required before review.")
    if not str(record.get("source_url", "")).strip():
        errors.append("source_url is required before review.")

    # cutting_data_status must remain not_imported
    cds = str(record.get("cutting_data_status", "")).strip()
    if cds and cds != "not_imported":
        errors.append(
            f"cutting_data_status must be 'not_imported', got '{cds}'. "
            "Do not import feeds/speeds through the review workflow."
        )

    return errors


def promote_record_for_review(
    record: dict[str, Any],
    *,
    review_status: str,
    reviewer: str,
    review_date: str | None = None,
    review_notes: str = "",
) -> dict[str, Any]:
    promoted: dict[str, Any] = {}
    for key, value in record.items():
        if isinstance(value, list):
            promoted[key] = list(value)
        elif isinstance(value, dict):
            promoted[key] = dict(value)
        else:
            promoted[key] = value
    promoted["verification_status"] = review_status
    promoted["cutting_data_status"] = "not_imported"
    promoted["reviewer"] = reviewer.strip()
    promoted["review_date"] = review_date or date.today().isoformat()
    promoted["review_notes"] = review_notes.strip()
    return promoted


def batch_review_records(
    records: list[dict[str, Any]],
    *,
    review_status: str,
    reviewer: str,
    review_date: str | None = None,
    review_notes: str = "",
) -> tuple[list[dict[str, Any]], list[str]]:
    promoted: list[dict[str, Any]] = []
    errors: list[str] = []

    for idx, record in enumerate(records):
        record_errors = validate_record_for_review(record, review_status)
        if record_errors:
            mpn = record.get("manufacturer_part_number", f"record_{idx}")
            for err in record_errors:
                errors.append(f"Record {idx} ({mpn}): {err}")
        else:
            promoted.append(
                promote_record_for_review(
                    record,
                    review_status=review_status,
                    reviewer=reviewer,
                    review_date=review_date,
                    review_notes=review_notes,
                )
            )

    return promoted, errors


def save_reviewed_tooling_records(
    brand_slug: str,
    records: list[dict[str, Any]],
    output_path: Path | None = None,
) -> Path:
    REVIEWED_DIR.mkdir(parents=True, exist_ok=True)
    slug = normalize_tool_query(brand_slug).replace(" ", "_").strip("_") or "unknown_brand"
    target = output_path or (REVIEWED_DIR / f"{slug}_reviewed_tooling_records.json")
    target.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    return target


def load_reviewed_tooling_records(reviewed_dir: Path | None = None) -> list[dict[str, Any]]:
    reviewed_dir = reviewed_dir or REVIEWED_DIR
    records: list[dict[str, Any]] = []
    if not reviewed_dir.exists():
        return records
    for path in sorted(reviewed_dir.glob("*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(raw, list):
            records.extend(raw)
    return records


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Batch review and promote tooling search records.")
    parser.add_argument("input_path", help="JSON file of imported tooling records to review.")
    parser.add_argument("--brand-slug", required=True, help="Brand slug for output file naming.")
    parser.add_argument("--reviewer", required=True, help="Reviewer name or identifier.")
    parser.add_argument(
        "--review-status",
        required=True,
        choices=sorted(ALLOWED_REVIEW_STATUSES),
        help="Review status to apply to all records.",
    )
    parser.add_argument("--review-date", default=None, help="Review date (ISO format). Defaults to today.")
    parser.add_argument("--review-notes", default="", help="Review notes to attach to all records.")
    parser.add_argument("--output-path", default=None, help="Custom output path.")
    parser.add_argument("--dry-run", action="store_true", help="Validate only, do not write output.")
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    records = load_tooling_records_for_review(args.input_path)
    promoted, errors = batch_review_records(
        records,
        review_status=args.review_status,
        reviewer=args.reviewer,
        review_date=args.review_date,
        review_notes=args.review_notes,
    )

    if errors:
        print("Review errors:")
        for error in errors:
            print(f"  {error}")
        return 1

    if args.dry_run:
        print(f"Dry run: {len(promoted)} records would be promoted to '{args.review_status}'.")
        return 0

    output_path = Path(args.output_path) if args.output_path else None
    written_path = save_reviewed_tooling_records(args.brand_slug, promoted, output_path)
    print(f"Reviewed {len(promoted)} records written to: {written_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
