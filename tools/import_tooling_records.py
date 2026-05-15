from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from grade_engine.tooling_search import RECORDS_DIR, SCHEMA_FIELDS, normalize_tool_query


REQUIRED_NON_EMPTY_FIELDS = [
    "brand",
    "tool_category",
    "manufacturer_part_number",
    "source_label",
    "source_url",
    "verification_status",
    "cutting_data_status",
]
LIST_FIELDS = {
    "material_fit": "upper",
    "operation_fit": "normalized",
    "geometry_tags": "normalized",
    "holder_compatibility": "plain",
}
FORBIDDEN_FIELD_TERMS = ("feed", "speed", "sfm", "rpm", "ipr", "ipm", "vc", "fz")


def load_import_rows(input_path: str | Path) -> list[dict[str, Any]]:
    path = Path(input_path)
    if path.suffix.lower() == ".csv":
        return _load_csv_rows(path)
    if path.suffix.lower() == ".json":
        return _load_json_rows(path)
    raise ValueError(f"Unsupported import format: {path.suffix}")


def validate_import_rows(rows: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    if not rows:
        return ["No tooling records found in import file."]

    for row_index, row in enumerate(rows, start=1):
        row_errors = validate_import_row(row, row_index=row_index)
        errors.extend(row_errors)
    return errors


def validate_import_row(row: dict[str, Any], row_index: int = 1) -> list[str]:
    errors: list[str] = []
    missing_fields = [field for field in SCHEMA_FIELDS if field not in row]
    if missing_fields:
        errors.append(f"Row {row_index}: missing required fields: {', '.join(missing_fields)}")

    forbidden_fields = [field for field in row if _field_contains_forbidden_term(field)]
    if forbidden_fields:
        errors.append(f"Row {row_index}: forbidden feed/speed fields: {', '.join(sorted(forbidden_fields))}")

    for field in REQUIRED_NON_EMPTY_FIELDS:
        if not str(row.get(field, "")).strip():
            errors.append(f"Row {row_index}: required field '{field}' must not be empty")

    return errors


def normalize_import_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized_rows: list[dict[str, Any]] = []
    for row in rows:
        normalized_rows.append(normalize_import_row(row))
    return normalized_rows


def normalize_import_row(row: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for field in SCHEMA_FIELDS:
        value = row.get(field)
        if field in LIST_FIELDS:
            normalized[field] = _normalize_list_field(value, LIST_FIELDS[field])
        elif field == "tool_category":
            normalized[field] = normalize_tool_query(str(value or "")).replace(" ", "_")
        elif field == "dimensions":
            normalized[field] = _normalize_dimensions(value)
        else:
            normalized[field] = str(value or "").strip()
    return normalized


def import_tooling_records(
    input_path: str | Path,
    *,
    output_path: str | Path | None = None,
    dry_run: bool = True,
) -> dict[str, Any]:
    rows = load_import_rows(input_path)
    errors = validate_import_rows(rows)
    normalized_rows = normalize_import_rows(rows) if not errors else []

    result = {
        "input_path": str(Path(input_path)),
        "record_count": len(rows),
        "normalized_record_count": len(normalized_rows),
        "dry_run": dry_run,
        "errors": errors,
        "output_path": None,
    }

    if errors or dry_run:
        return result

    target_path = Path(output_path) if output_path else RECORDS_DIR / "imported_tooling_records.json"
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(json.dumps(normalized_rows, indent=2), encoding="utf-8")
    result["output_path"] = str(target_path)
    return result


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate and normalize bulk tooling-record imports.")
    parser.add_argument("input_path", help="CSV or JSON file containing tooling search records.")
    parser.add_argument(
        "--output-path",
        default="",
        help="Optional output JSON path. Defaults to tool_data/tooling_search/records/imported_tooling_records.json",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write normalized JSON output. Default behavior is dry-run validation only.",
    )
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()
    result = import_tooling_records(
        args.input_path,
        output_path=args.output_path or None,
        dry_run=not args.write,
    )
    print(json.dumps(result, indent=2))
    return 1 if result["errors"] else 0


def _load_csv_rows(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            return []
        _raise_for_forbidden_fieldnames(reader.fieldnames)
        rows = []
        for row in reader:
            rows.append({key: value for key, value in row.items()})
        return rows


def _load_json_rows(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("JSON import file must contain a list of tooling records.")
    if payload:
        _raise_for_forbidden_fieldnames(payload[0].keys())
    return payload


def _raise_for_forbidden_fieldnames(fieldnames: list[str] | Any) -> None:
    forbidden_fields = [field for field in fieldnames if _field_contains_forbidden_term(str(field))]
    if forbidden_fields:
        raise ValueError("Forbidden feed/speed fields present: " + ", ".join(sorted(forbidden_fields)))


def _field_contains_forbidden_term(field_name: str) -> bool:
    lowered = normalize_tool_query(field_name)
    return any(term in lowered for term in FORBIDDEN_FIELD_TERMS)


def _normalize_list_field(value: Any, mode: str) -> list[str]:
    if value in (None, "", []):
        return []
    if isinstance(value, list):
        parts = [str(item).strip() for item in value if str(item).strip()]
    else:
        raw = str(value).replace(";", "|").replace(",", "|")
        parts = [item.strip() for item in raw.split("|") if item.strip()]

    if mode == "upper":
        return [item.upper() for item in parts]
    if mode == "normalized":
        return [normalize_tool_query(item).replace(" ", "_") for item in parts]
    return parts


def _normalize_dimensions(value: Any) -> dict[str, Any]:
    if value in (None, "", {}):
        return {}
    if isinstance(value, dict):
        return value
    text = str(value).strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid dimensions JSON: {text}") from exc
    if not isinstance(parsed, dict):
        raise ValueError("Dimensions field must decode to a JSON object.")
    return parsed


if __name__ == "__main__":
    raise SystemExit(main())
