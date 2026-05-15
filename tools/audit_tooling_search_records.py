from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from grade_engine.tooling_search import RECORDS_DIR, SCHEMA_FIELDS, normalize_tool_query


AUDIT_REPORTS_DIR = RECORDS_DIR.parent / "audit_reports"

REQUIRED_NON_EMPTY_FIELDS = [
    "brand",
    "tool_category",
    "manufacturer_part_number",
    "source_label",
    "source_url",
    "verification_status",
    "cutting_data_status",
]

VALID_VERIFICATION_STATUSES = frozenset({
    "verified_source_page_record",
    "sample_family_level_not_catalog_verified",
    "reviewed_exact_tool_candidate",
    "reviewed_family_level_candidate",
})

VALID_CUTTING_DATA_STATUSES = frozenset({
    "not_imported",
})

FORBIDDEN_FIELD_TERMS = ("feed", "speed", "sfm", "rpm", "ipr", "ipm", "vc", "fz")

LIST_FIELDS = frozenset({"material_fit", "operation_fit", "geometry_tags", "holder_compatibility"})


def _field_contains_forbidden_term(field_name: str) -> bool:
    lowered = normalize_tool_query(str(field_name))
    return any(term in lowered for term in FORBIDDEN_FIELD_TERMS)


def audit_record(
    record: dict[str, Any],
    record_index: int,
    source_file: str,
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []

    def _issue(issue_type: str, detail: str) -> dict[str, Any]:
        return {
            "file": source_file,
            "record_index": record_index,
            "issue_type": issue_type,
            "detail": detail,
        }

    # Missing schema fields
    missing = [f for f in SCHEMA_FIELDS if f not in record]
    if missing:
        issues.append(_issue("missing_schema_fields", f"Missing fields: {', '.join(missing)}"))

    # Required non-empty fields
    for field in REQUIRED_NON_EMPTY_FIELDS:
        if not str(record.get(field, "")).strip():
            issues.append(_issue("missing_required_value", f"Required field '{field}' is empty or missing."))

    # Explicit source traceability check
    for field in ("source_label", "source_url"):
        if field in record and not str(record.get(field, "")).strip():
            pass  # already covered above

    # verification_status validity
    vs = str(record.get("verification_status", "")).strip()
    if vs and vs not in VALID_VERIFICATION_STATUSES:
        issues.append(_issue(
            "invalid_verification_status",
            f"'{vs}' is not an allowed verification_status. Allowed: {sorted(VALID_VERIFICATION_STATUSES)}",
        ))

    # cutting_data_status validity
    cds = str(record.get("cutting_data_status", "")).strip()
    if cds and cds not in VALID_CUTTING_DATA_STATUSES:
        issues.append(_issue(
            "invalid_cutting_data_status",
            f"'{cds}' is not an allowed cutting_data_status. Allowed: {sorted(VALID_CUTTING_DATA_STATUSES)}",
        ))

    # Forbidden feed/speed fields
    forbidden = sorted(f for f in record if _field_contains_forbidden_term(str(f)))
    if forbidden:
        issues.append(_issue("forbidden_feed_speed_fields", f"Forbidden fields: {', '.join(forbidden)}"))

    # List field types
    for list_field in LIST_FIELDS:
        if list_field not in record:
            continue
        value = record[list_field]
        if value is not None and not isinstance(value, list):
            issues.append(_issue(
                "invalid_list_field_type",
                f"Field '{list_field}' must be a list, got {type(value).__name__}.",
            ))

    # Empty operation_fit / material_fit
    if isinstance(record.get("operation_fit"), list) and len(record["operation_fit"]) == 0:
        issues.append(_issue("missing_operation_fit", "operation_fit is empty; at least one operation tag required."))
    if isinstance(record.get("material_fit"), list) and len(record["material_fit"]) == 0:
        issues.append(_issue("missing_material_fit", "material_fit is empty; at least one ISO material group required."))

    return issues


def audit_tooling_search_records(records_dir: Path | None = None) -> dict[str, Any]:
    records_dir = records_dir or RECORDS_DIR
    all_issues: list[dict[str, Any]] = []
    file_summaries: list[dict[str, Any]] = []
    # (brand, mpn) -> list of location dicts for duplicate detection.
    # Only top-level files are included: records in records/reviewed/ are a staging
    # tier and their MPNs are expected to duplicate top-level records while awaiting
    # promotion.
    seen_pairs: dict[tuple[str, str], list[dict[str, Any]]] = {}
    top_level_files = set(records_dir.glob("*.json"))

    json_files = sorted(records_dir.rglob("*.json"))

    for json_path in json_files:
        try:
            raw = json.loads(json_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            all_issues.append({
                "file": json_path.name,
                "record_index": None,
                "issue_type": "json_parse_error",
                "detail": str(exc),
            })
            continue

        if not isinstance(raw, list):
            all_issues.append({
                "file": json_path.name,
                "record_index": None,
                "issue_type": "invalid_file_format",
                "detail": "File must contain a JSON array.",
            })
            continue

        file_issues: list[dict[str, Any]] = []
        for idx, record in enumerate(raw):
            record_issues = audit_record(record, idx, json_path.name)
            file_issues.extend(record_issues)

            brand = str(record.get("brand", "")).strip()
            mpn = str(record.get("manufacturer_part_number", "")).strip()
            if brand and mpn and json_path in top_level_files:
                location = {"file": json_path.name, "record_index": idx}
                seen_pairs.setdefault((brand, mpn), []).append(location)

        all_issues.extend(file_issues)
        try:
            rel = str(json_path.relative_to(records_dir))
        except ValueError:
            rel = json_path.name
        file_summaries.append({
            "file": rel,
            "record_count": len(raw),
            "issue_count": len(file_issues),
        })

    # Duplicate MPN within same brand
    for (brand, mpn), locations in seen_pairs.items():
        if len(locations) > 1:
            all_issues.append({
                "file": locations[0]["file"],
                "record_index": locations[0]["record_index"],
                "issue_type": "duplicate_manufacturer_part_number",
                "detail": (
                    f"Duplicate manufacturer_part_number '{mpn}' for brand '{brand}' "
                    f"found in {len(locations)} locations: {locations}"
                ),
            })

    return {
        "audit_date": date.today().isoformat(),
        "records_dir": str(records_dir),
        "files_audited": len(json_files),
        "file_summaries": file_summaries,
        "total_issues": len(all_issues),
        "issues": all_issues,
    }


def write_audit_report(report: dict[str, Any], output_path: Path | None = None) -> Path:
    output_path = output_path or (AUDIT_REPORTS_DIR / "tooling_search_audit_report.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return output_path


def print_audit_summary(report: dict[str, Any]) -> None:
    print(f"Audit date:        {report['audit_date']}")
    print(f"Records directory: {report['records_dir']}")
    print(f"Files audited:     {report['files_audited']}")
    print()
    for s in report.get("file_summaries", []):
        status = "OK" if s["issue_count"] == 0 else f"{s['issue_count']} issues"
        print(f"  {s['file']:50s}  {s['record_count']:3d} records  {status}")
    print()
    total = report["total_issues"]
    print(f"Total issues: {total}")
    if report["issues"]:
        print()
        for issue in report["issues"]:
            print(
                f"  [{issue['issue_type']}] {issue['file']} "
                f"record {issue.get('record_index', '?')}: {issue['detail']}"
            )


def main() -> int:
    report = audit_tooling_search_records()
    output_path = write_audit_report(report)
    print_audit_summary(report)
    print()
    print(f"Audit report written to: {output_path}")
    return 0 if report["total_issues"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
