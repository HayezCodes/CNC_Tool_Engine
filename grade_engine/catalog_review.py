import json
from pathlib import Path
from typing import Any

from tools.catalog_ingestion import PROHIBITED_CUTTING_DATA_FIELDS


REVIEWED_ROOT = Path(__file__).resolve().parent.parent / "tool_data" / "catalog_ingestion" / "reviewed"


def load_reviewed_catalog_records() -> list[dict]:
    records: list[dict] = []
    if not REVIEWED_ROOT.exists():
        return records

    for path in sorted(REVIEWED_ROOT.glob("*.json")):
        if path.name == ".gitkeep":
            continue
        loaded = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(loaded, list):
            continue
        for record in loaded:
            if _is_display_safe_reviewed_record(record):
                records.append(record)
    return records


def get_reviewed_catalog_summary() -> dict:
    records = load_reviewed_catalog_records()
    return {
        "total_records": len(records),
        "brands": sorted({record.get("brand", "") for record in records if record.get("brand")}),
        "tool_categories": sorted({record.get("tool_category", "") for record in records if record.get("tool_category")}),
        "materials": sorted({item for record in records for item in _list_values(record.get("material_fit", []))}),
        "operations": sorted({item for record in records for item in _list_values(record.get("operation_fit", []))}),
    }


def filter_reviewed_catalog_records(
    brand: str | None = None,
    tool_category: str | None = None,
    material_group: str | None = None,
    operation: str | None = None,
) -> list[dict]:
    records = load_reviewed_catalog_records()
    if brand:
        records = [record for record in records if _matches(record.get("brand", ""), brand)]
    if tool_category:
        records = [record for record in records if _matches(record.get("tool_category", ""), tool_category)]
    if material_group:
        records = [
            record
            for record in records
            if _normalize(material_group) in {_normalize(item) for item in _list_values(record.get("material_fit", []))}
        ]
    if operation:
        records = [
            record
            for record in records
            if _normalize(operation) in {_normalize(item) for item in _list_values(record.get("operation_fit", []))}
        ]
    return records


def _is_display_safe_reviewed_record(record: Any) -> bool:
    if not isinstance(record, dict):
        return False
    if record.get("verification_status") != "reviewed_family_level":
        return False
    return not _find_prohibited_cutting_data_fields(record)


def _find_prohibited_cutting_data_fields(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            if _normalize_key(key) in PROHIBITED_CUTTING_DATA_FIELDS:
                found.add(str(key))
            found.update(_find_prohibited_cutting_data_fields(child))
    elif isinstance(value, list):
        for child in value:
            found.update(_find_prohibited_cutting_data_fields(child))
    return found


def _list_values(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    return []


def _matches(value: object, expected: str) -> bool:
    return _normalize(value) == _normalize(expected)


def _normalize(value: object) -> str:
    return str(value).strip().lower()


def _normalize_key(value: object) -> str:
    return str(value).strip().lower().replace(" ", "_").replace("-", "_")
