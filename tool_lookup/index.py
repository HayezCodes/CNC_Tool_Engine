from __future__ import annotations

import json
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from typing import Any

from .normalize import normalize_tool_number


ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "tool_data"
LOOKUP_PATH = DATA_ROOT / "lookup" / "manufacturer_lookup.json"

NORMALIZED_SOURCES = [
    ("normalized/turning/inserts.json", "turning_insert"),
    ("normalized/drilling/solid_drills.json", "solid_drill"),
    ("normalized/drilling/indexable_drills.json", "indexable_drill"),
    ("normalized/milling/endmills.json", "endmill"),
    ("normalized/milling/indexable_cutters.json", "indexable_milling_cutter"),
    ("normalized/grooving/inserts.json", "grooving_insert"),
    ("normalized/threading/inserts.json", "threading_insert"),
]


def _load_json(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else []


def _coerce_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value if item not in (None, "")]
    return [str(value)]


def _build_reference(row: dict[str, Any]) -> str:
    for key in ("designation_family", "series", "id"):
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _build_search_hint(brand: str, reference: str, tool_category: str) -> str:
    parts = [part for part in [brand, reference, tool_category] if part]
    return " ".join(parts)


def _normalized_record(row: dict[str, Any], source_path: str, fallback_category: str) -> dict[str, Any]:
    brand = str(row.get("brand", "")).strip()
    series = str(row.get("series", "")).strip()
    designation = str(row.get("designation_family", "")).strip()
    reference = _build_reference(row)
    tool_category = str(row.get("tool_category", fallback_category)).strip() or fallback_category
    geometry = deepcopy(row.get("geometry", {})) if isinstance(row.get("geometry"), dict) else {}
    application = deepcopy(row.get("application", {})) if isinstance(row.get("application"), dict) else {}
    application.setdefault("operations", [])
    application["operations"] = _coerce_list(application.get("operations"))
    application["strategy"] = str(application.get("strategy", "")).strip()
    iso_groups = _coerce_list(row.get("materials", {}).get("iso_groups", []))
    grades = _coerce_list(row.get("recommended_grades", []))
    manufacturer_number = reference
    return {
        "brand": brand,
        "manufacturer_number": manufacturer_number,
        "manufacturer_reference": reference,
        "normalized_number": normalize_tool_number(manufacturer_number),
        "tool_category": tool_category,
        "series": series,
        "designation": designation,
        "grade": grades[0] if grades else "",
        "geometry": geometry,
        "materials": {"iso_groups": iso_groups},
        "application": application,
        "source_catalog": source_path,
        "search_hint": _build_search_hint(brand, reference, tool_category),
        "id": str(row.get("id", "")).strip(),
    }


def _lookup_file_records() -> list[dict[str, Any]]:
    rows = _load_json(LOOKUP_PATH)
    records: list[dict[str, Any]] = []
    for row in rows:
        brand = str(row.get("brand", "")).strip()
        manufacturer_number = str(row.get("manufacturer_number", "")).strip()
        normalized_number = str(row.get("normalized_number", "")).strip() or normalize_tool_number(manufacturer_number)
        tool_category = str(row.get("tool_category", "")).strip()
        series = str(row.get("series", "")).strip()
        designation = str(row.get("designation", "")).strip()
        grade = str(row.get("grade", "")).strip()
        geometry = deepcopy(row.get("geometry", {})) if isinstance(row.get("geometry"), dict) else {}
        application = deepcopy(row.get("application", {})) if isinstance(row.get("application"), dict) else {}
        application.setdefault("operations", [])
        application["operations"] = _coerce_list(application.get("operations"))
        application["strategy"] = str(application.get("strategy", "")).strip()
        iso_groups = _coerce_list(row.get("materials", {}).get("iso_groups", []))
        manufacturer_reference = manufacturer_number or designation or series
        records.append(
            {
                "brand": brand,
                "manufacturer_number": manufacturer_number,
                "manufacturer_reference": manufacturer_reference,
                "normalized_number": normalized_number,
                "tool_category": tool_category,
                "series": series,
                "designation": designation,
                "grade": grade,
                "geometry": geometry,
                "materials": {"iso_groups": iso_groups},
                "application": application,
                "source_catalog": str(row.get("source_catalog", "")).strip(),
                "search_hint": str(row.get("search_hint", "")).strip()
                or _build_search_hint(brand, manufacturer_reference, tool_category),
                "id": str(row.get("id", "")).strip(),
            }
        )
    return records


@lru_cache(maxsize=1)
def load_lookup_records() -> list[dict[str, Any]]:
    records = _lookup_file_records()
    for relative_path, fallback_category in NORMALIZED_SOURCES:
        rows = _load_json(DATA_ROOT / relative_path)
        for row in rows:
            records.append(_normalized_record(row, relative_path, fallback_category))
    return records
