import json
import re
from pathlib import Path
from typing import Any


DATA_ROOT = Path(__file__).resolve().parent.parent / "tool_data"
CATALOG_INGESTION_ROOT = DATA_ROOT / "catalog_ingestion"
CATALOG_SOURCES_PATH = CATALOG_INGESTION_ROOT / "catalog_sources.json"
STAGED_ROOT = CATALOG_INGESTION_ROOT / "staged"

STAGED_DEFAULTS = {
    "brand": "",
    "source_label": "",
    "source_url": "",
    "source_type": "",
    "tool_category": "",
    "family_name": "",
    "operation_fit": [],
    "material_fit": [],
    "strategy_fit": [],
    "coating_or_grade": "",
    "geometry_tags": [],
    "dimension_summary": "",
    "catalog_number": "",
    "cutting_data_status": "not_imported",
    "verification_status": "staged_unreviewed",
    "review_notes": "",
    "source_page_reference": "",
}

PROHIBITED_CUTTING_DATA_FIELDS = {
    "speed",
    "speeds",
    "feed",
    "feeds",
    "sfm",
    "rpm",
    "ipr",
    "ipm",
    "fpt",
    "feed_per_tooth",
    "chip_load",
    "surface_speed",
    "cutting_speed",
}


def load_catalog_sources(data_root: Path | None = None) -> list[dict]:
    path = _catalog_sources_path(data_root)
    records = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise ValueError(f"Catalog source registry must be a list: {path}")
    return records


def list_sources_by_brand(brand: str) -> list[dict]:
    target = _normalize(brand)
    return [
        source
        for source in load_catalog_sources()
        if target in _normalize(source.get("brand", ""))
    ]


def build_staged_record(**values: Any) -> dict:
    record = {
        key: _copy_default(value)
        for key, value in STAGED_DEFAULTS.items()
    }
    for key, value in values.items():
        record[key] = value
    record["cutting_data_status"] = "not_imported"
    record["verification_status"] = "staged_unreviewed"
    return record


def validate_staged_record(record: dict) -> list[str]:
    errors: list[str] = []
    for field in ["brand", "source_url", "tool_category", "family_name"]:
        if not str(record.get(field, "")).strip():
            errors.append(f"{field} is required.")

    if record.get("verification_status") != "staged_unreviewed":
        errors.append("verification_status must start as staged_unreviewed.")

    if record.get("cutting_data_status") != "not_imported":
        errors.append("cutting_data_status must default to not_imported.")

    prohibited_fields = sorted(_find_prohibited_cutting_data_fields(record))
    if prohibited_fields:
        errors.append("Exact feeds/speeds are not allowed in staged records yet: " + ", ".join(prohibited_fields))

    if str(record.get("catalog_number", "")).strip() and not str(record.get("source_page_reference", "")).strip():
        errors.append("source_page_reference is required when catalog_number is present.")

    return errors


def save_staged_records(brand: str, records: list[dict], data_root: Path | None = None) -> Path:
    staged_root = _staged_root(data_root)
    staged_root.mkdir(parents=True, exist_ok=True)

    all_errors: list[str] = []
    for index, record in enumerate(records):
        errors = validate_staged_record(record)
        all_errors.extend(f"record {index}: {error}" for error in errors)
    if all_errors:
        raise ValueError("; ".join(all_errors))

    path = staged_root / f"{_slugify(brand)}_staged_records.json"
    path.write_text(json.dumps(records, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _catalog_sources_path(data_root: Path | None) -> Path:
    if data_root is None:
        return CATALOG_SOURCES_PATH
    return data_root / "catalog_ingestion" / "catalog_sources.json"


def _staged_root(data_root: Path | None) -> Path:
    if data_root is None:
        return STAGED_ROOT
    return data_root / "catalog_ingestion" / "staged"


def _copy_default(value: Any) -> Any:
    if isinstance(value, list):
        return list(value)
    if isinstance(value, dict):
        return dict(value)
    return value


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


def _normalize(value: str) -> str:
    return value.strip().lower()


def _normalize_key(value: object) -> str:
    return str(value).strip().lower().replace(" ", "_").replace("-", "_")


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "unknown_brand"
