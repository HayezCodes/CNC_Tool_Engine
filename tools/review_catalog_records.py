import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.catalog_ingestion import PROHIBITED_CUTTING_DATA_FIELDS


REVIEWED_ROOT = Path(__file__).resolve().parent.parent / "tool_data" / "catalog_ingestion" / "reviewed"


def load_staged_records(path: str | Path) -> list[dict]:
    records = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise ValueError(f"Staged records must be a list: {path}")
    return records


def summarize_staged_records(records: list[dict]) -> dict:
    return {
        "total_records": len(records),
        "brands": sorted({record.get("brand", "") for record in records if record.get("brand")}),
        "tool_categories": sorted({record.get("tool_category", "") for record in records if record.get("tool_category")}),
        "family_names": sorted({record.get("family_name", "") for record in records if record.get("family_name")}),
        "verification_statuses": sorted({record.get("verification_status", "") for record in records if record.get("verification_status")}),
        "cutting_data_statuses": sorted({record.get("cutting_data_status", "") for record in records if record.get("cutting_data_status")}),
    }


def mark_record_reviewed(record: dict, reviewer: str, notes: str) -> dict:
    reviewed = _copy_record(record)
    reviewed["verification_status"] = "reviewed_family_level"
    reviewed["cutting_data_status"] = record.get("cutting_data_status") or "not_imported"
    reviewed["reviewer"] = reviewer
    reviewed["review_date"] = date.today().isoformat()
    reviewed["review_notes"] = notes
    return reviewed


def validate_reviewed_record(record: dict) -> list[str]:
    errors: list[str] = []
    if record.get("verification_status") != "reviewed_family_level":
        errors.append("verification_status must be reviewed_family_level.")
    if record.get("cutting_data_status") != "not_imported":
        errors.append("cutting_data_status must remain not_imported unless exact cutting data review exists.")
    for field in ["reviewer", "review_date", "source_url", "source_label"]:
        if not str(record.get(field, "")).strip():
            errors.append(f"{field} is required.")
    if str(record.get("catalog_number", "")).strip() and not str(record.get("source_page_reference", "")).strip():
        errors.append("source_page_reference is required when catalog_number is present.")

    prohibited_fields = sorted(_find_prohibited_cutting_data_fields(record))
    if prohibited_fields:
        errors.append("Exact feeds/speeds are not allowed in reviewed family-level records: " + ", ".join(prohibited_fields))
    return errors


def save_reviewed_records(brand_slug: str, records: list[dict]) -> Path:
    REVIEWED_ROOT.mkdir(parents=True, exist_ok=True)
    all_errors: list[str] = []
    for index, record in enumerate(records):
        all_errors.extend(f"record {index}: {error}" for error in validate_reviewed_record(record))
    if all_errors:
        raise ValueError("; ".join(all_errors))

    path = REVIEWED_ROOT / f"{_slugify(brand_slug)}_reviewed_records.json"
    path.write_text(json.dumps(records, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _copy_record(record: dict) -> dict:
    copied: dict[str, Any] = {}
    for key, value in record.items():
        if isinstance(value, list):
            copied[key] = list(value)
        elif isinstance(value, dict):
            copied[key] = dict(value)
        else:
            copied[key] = value
    return copied


def _find_prohibited_cutting_data_fields(value: Any, prefix: str = "") -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            normalized_key = _normalize_key(key)
            child_path = f"{prefix}.{key}" if prefix else str(key)
            if normalized_key in PROHIBITED_CUTTING_DATA_FIELDS:
                found.add(child_path)
            found.update(_find_prohibited_cutting_data_fields(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.update(_find_prohibited_cutting_data_fields(child, f"{prefix}[{index}]"))
    return found


def _print_summary(summary: dict) -> None:
    print(f"total records: {summary['total_records']}")
    print("brands: " + _join(summary["brands"]))
    print("tool categories: " + _join(summary["tool_categories"]))
    print("family names: " + _join(summary["family_names"]))
    print("verification statuses: " + _join(summary["verification_statuses"]))
    print("cutting data statuses: " + _join(summary["cutting_data_statuses"]))


def _join(values: list[str]) -> str:
    return ", ".join(values) if values else "(none)"


def _normalize_key(value: object) -> str:
    return str(value).strip().lower().replace(" ", "_").replace("-", "_")


def _slugify(value: str) -> str:
    return _normalize_key(value).strip("_") or "unknown_brand"


def main() -> None:
    parser = argparse.ArgumentParser(description="Review staged catalog records.")
    parser.add_argument("path", help="Path to staged JSON records.")
    parser.add_argument("--summary", action="store_true", help="Print a staged-record summary.")
    args = parser.parse_args()

    records = load_staged_records(args.path)
    if args.summary:
        _print_summary(summarize_staged_records(records))


if __name__ == "__main__":
    main()
