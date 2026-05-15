from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any


DATA_ROOT = Path(__file__).resolve().parent.parent / "tool_data" / "tooling_search"
RECORDS_DIR = DATA_ROOT / "records"
TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
SCHEMA_FIELDS = [
    "brand",
    "tool_category",
    "manufacturer_part_number",
    "series",
    "family_name",
    "designation",
    "grade",
    "chipbreaker",
    "coating",
    "material_fit",
    "operation_fit",
    "geometry_tags",
    "dimensions",
    "holder_compatibility",
    "coolant_capability",
    "source_label",
    "source_url",
    "source_page_reference",
    "verification_status",
    "cutting_data_status",
    "notes",
]
SEARCHABLE_TEXT_FIELDS = [
    "brand",
    "manufacturer_part_number",
    "series",
    "family_name",
    "designation",
    "grade",
    "chipbreaker",
    "coating",
    "tool_category",
    "source_label",
    "notes",
]
SEARCHABLE_LIST_FIELDS = [
    "material_fit",
    "operation_fit",
    "geometry_tags",
    "holder_compatibility",
]


def normalize_tool_query(query: str) -> str:
    if not query:
        return ""
    lowered = str(query).strip().lower()
    lowered = re.sub(r"[^a-z0-9]+", " ", lowered)
    return " ".join(lowered.split())


def _tokenize(value: str) -> list[str]:
    return TOKEN_PATTERN.findall(normalize_tool_query(value))


def _normalize_record(record: dict[str, Any]) -> dict[str, Any]:
    normalized = {field: record.get(field) for field in SCHEMA_FIELDS}
    normalized["brand"] = str(normalized.get("brand") or "").strip()
    normalized["tool_category"] = normalize_tool_query(str(normalized.get("tool_category") or "")).replace(" ", "_")
    normalized["manufacturer_part_number"] = str(normalized.get("manufacturer_part_number") or "").strip()
    normalized["series"] = str(normalized.get("series") or "").strip()
    normalized["family_name"] = str(normalized.get("family_name") or "").strip()
    normalized["designation"] = str(normalized.get("designation") or "").strip()
    normalized["grade"] = str(normalized.get("grade") or "").strip()
    normalized["chipbreaker"] = str(normalized.get("chipbreaker") or "").strip()
    normalized["coating"] = str(normalized.get("coating") or "").strip()
    normalized["material_fit"] = [str(value).strip().upper() for value in (normalized.get("material_fit") or []) if str(value).strip()]
    normalized["operation_fit"] = [
        normalize_tool_query(str(value)).replace(" ", "_")
        for value in (normalized.get("operation_fit") or [])
        if str(value).strip()
    ]
    normalized["geometry_tags"] = [
        normalize_tool_query(str(value)).replace(" ", "_")
        for value in (normalized.get("geometry_tags") or [])
        if str(value).strip()
    ]
    normalized["dimensions"] = normalized.get("dimensions") or {}
    normalized["holder_compatibility"] = [
        str(value).strip() for value in (normalized.get("holder_compatibility") or []) if str(value).strip()
    ]
    normalized["coolant_capability"] = str(normalized.get("coolant_capability") or "unknown").strip()
    normalized["source_label"] = str(normalized.get("source_label") or "").strip()
    normalized["source_url"] = str(normalized.get("source_url") or "").strip()
    normalized["source_page_reference"] = str(normalized.get("source_page_reference") or "").strip()
    normalized["verification_status"] = str(normalized.get("verification_status") or "").strip()
    normalized["cutting_data_status"] = str(normalized.get("cutting_data_status") or "").strip()
    normalized["notes"] = str(normalized.get("notes") or "").strip()
    normalized["_normalized_blob"] = _build_record_blob(normalized)
    normalized["_search_tokens"] = set(_tokenize(normalized["_normalized_blob"]))
    return normalized


def _build_record_blob(record: dict[str, Any]) -> str:
    parts: list[str] = []
    for field in SEARCHABLE_TEXT_FIELDS:
        value = record.get(field)
        if value:
            parts.append(str(value))
    for field in SEARCHABLE_LIST_FIELDS:
        for value in record.get(field, []) or []:
            parts.append(str(value))
    return " ".join(parts)


@lru_cache(maxsize=1)
def load_tooling_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if not RECORDS_DIR.exists():
        return records
    for path in sorted(RECORDS_DIR.glob("*.json")):
        raw_records = json.loads(path.read_text(encoding="utf-8"))
        for raw_record in raw_records:
            records.append(_normalize_record(raw_record))
    return records


def build_tooling_search_index(records: list[dict[str, Any]]) -> dict[str, Any]:
    token_index: dict[str, list[int]] = {}
    for idx, record in enumerate(records):
        for token in record.get("_search_tokens", set()):
            token_index.setdefault(token, []).append(idx)
    return {
        "record_count": len(records),
        "token_index": token_index,
        "tokens": sorted(token_index.keys()),
    }


def _normalize_filter_values(filters: dict[str, Any] | None) -> dict[str, Any]:
    if not filters:
        return {}

    normalized: dict[str, Any] = {}
    for key, value in filters.items():
        if value in (None, "", [], set(), tuple(), {}):
            continue
        if key == "material_group":
            normalized[key] = str(value).strip().upper()
        elif key in {"operation", "tool_category", "geometry_tag"}:
            normalized[key] = normalize_tool_query(str(value)).replace(" ", "_")
        elif key in {"brand", "manufacturer_part_number", "designation", "grade", "chipbreaker", "coating"}:
            normalized[key] = normalize_tool_query(str(value))
        else:
            normalized[key] = value
    return normalized


def filter_tooling_records(records: list[dict[str, Any]], filters: dict | None = None) -> list[dict[str, Any]]:
    normalized_filters = _normalize_filter_values(filters)
    if not normalized_filters:
        return list(records)

    filtered: list[dict[str, Any]] = []
    for record in records:
        if "brand" in normalized_filters and normalized_filters["brand"] not in normalize_tool_query(record["brand"]):
            continue
        if "manufacturer_part_number" in normalized_filters and normalized_filters["manufacturer_part_number"] not in normalize_tool_query(record["manufacturer_part_number"]):
            continue
        if "designation" in normalized_filters and normalized_filters["designation"] not in normalize_tool_query(record["designation"]):
            continue
        if "tool_category" in normalized_filters and normalized_filters["tool_category"] != record["tool_category"]:
            continue
        if "material_group" in normalized_filters and normalized_filters["material_group"] not in record["material_fit"]:
            continue
        if "operation" in normalized_filters and normalized_filters["operation"] not in record["operation_fit"]:
            continue
        if "grade" in normalized_filters and normalized_filters["grade"] not in normalize_tool_query(record["grade"]):
            continue
        if "chipbreaker" in normalized_filters and normalized_filters["chipbreaker"] not in normalize_tool_query(record["chipbreaker"]):
            continue
        if "coating" in normalized_filters and normalized_filters["coating"] not in normalize_tool_query(record["coating"]):
            continue
        if "geometry_tag" in normalized_filters and normalized_filters["geometry_tag"] not in record["geometry_tags"]:
            continue
        filtered.append(record)
    return filtered


def search_tooling_records(query: str, filters: dict | None = None) -> list[dict[str, Any]]:
    records = filter_tooling_records(load_tooling_records(), filters)
    normalized_query = normalize_tool_query(query)
    if not normalized_query:
        return records

    query_tokens = set(_tokenize(normalized_query))
    scored: list[tuple[int, dict[str, Any]]] = []
    for record in records:
        score = 0
        normalized_brand = normalize_tool_query(record["brand"])
        normalized_part = normalize_tool_query(record["manufacturer_part_number"])
        normalized_designation = normalize_tool_query(record["designation"])

        if normalized_query == normalized_part and normalized_part:
            score += 12
        elif normalized_query and normalized_query in normalized_part and normalized_part:
            score += 8

        if normalized_query == normalized_designation and normalized_designation:
            score += 10
        elif normalized_query and normalized_query in normalized_designation and normalized_designation:
            score += 6

        if normalized_query and normalized_query in normalized_brand:
            score += 5

        score += len(query_tokens.intersection(record.get("_search_tokens", set()))) * 2
        if score <= 0:
            continue
        scored.append((score, record))

    scored.sort(
        key=lambda item: (
            -item[0],
            item[1]["brand"],
            item[1]["manufacturer_part_number"],
            item[1]["designation"],
        )
    )
    return [record for _, record in scored]


def explain_tool_match(record: dict, query: str, filters: dict | None = None) -> list[str]:
    reasons: list[str] = []
    normalized_query = normalize_tool_query(query)
    query_tokens = set(_tokenize(normalized_query))

    if normalized_query:
        if normalized_query == normalize_tool_query(record.get("manufacturer_part_number", "")):
            reasons.append("exact manufacturer part number match")
        elif normalized_query in normalize_tool_query(record.get("manufacturer_part_number", "")) and record.get("manufacturer_part_number"):
            reasons.append("manufacturer part number match")

        if normalized_query == normalize_tool_query(record.get("designation", "")):
            reasons.append("exact designation match")
        elif normalized_query in normalize_tool_query(record.get("designation", "")) and record.get("designation"):
            reasons.append("designation match")

        if normalized_query in normalize_tool_query(record.get("brand", "")):
            reasons.append("brand match")

        shared_tokens = sorted(query_tokens.intersection(record.get("_search_tokens", set())))
        if shared_tokens:
            reasons.append("shared search terms: " + ", ".join(shared_tokens[:5]))

    normalized_filters = _normalize_filter_values(filters)
    if "tool_category" in normalized_filters and normalized_filters["tool_category"] == record.get("tool_category"):
        reasons.append(f"tool category filter matched: {record['tool_category']}")
    if "material_group" in normalized_filters and normalized_filters["material_group"] in record.get("material_fit", []):
        reasons.append(f"material filter matched: {normalized_filters['material_group']}")
    if "operation" in normalized_filters and normalized_filters["operation"] in record.get("operation_fit", []):
        reasons.append(f"operation filter matched: {normalized_filters['operation']}")
    if "grade" in normalized_filters and normalized_filters["grade"] in normalize_tool_query(record.get("grade", "")):
        reasons.append("grade filter matched")
    if "chipbreaker" in normalized_filters and normalized_filters["chipbreaker"] in normalize_tool_query(record.get("chipbreaker", "")):
        reasons.append("chipbreaker filter matched")
    if "coating" in normalized_filters and normalized_filters["coating"] in normalize_tool_query(record.get("coating", "")):
        reasons.append("coating filter matched")
    if "geometry_tag" in normalized_filters and normalized_filters["geometry_tag"] in record.get("geometry_tags", []):
        reasons.append(f"geometry filter matched: {normalized_filters['geometry_tag']}")

    if record.get("verification_status"):
        reasons.append(f"verification status: {record['verification_status']}")

    return reasons or ["record available in tooling search foundation"]


def suggest_tool_candidates(
    operation: str,
    material_group: str,
    tool_category: str | None = None,
    brand: str | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Return exact-tool candidate records from the Enterprise Tooling Search index.

    Filters by operation_fit (operation) and material_fit (material_group).
    Optional tool_category and brand filters narrow results further. Records are
    ranked by match strength (operation/material presence plus field completeness)
    and returned up to limit.

    No forbidden feed/speed keys are ever returned — records come from the
    normalized index which enforces cutting_data_status = not_imported.
    """
    filters: dict[str, Any] = {
        "operation": operation,
        "material_group": material_group,
    }
    if tool_category:
        filters["tool_category"] = tool_category
    if brand:
        filters["brand"] = brand

    matched = filter_tooling_records(load_tooling_records(), filters)

    def _score(record: dict[str, Any]) -> int:
        score = 0
        norm_op = normalize_tool_query(operation).replace(" ", "_")
        if norm_op in record.get("operation_fit", []):
            score += 3
        if str(material_group).strip().upper() in record.get("material_fit", []):
            score += 2
        for field in ("grade", "chipbreaker", "coating", "series", "family_name", "designation"):
            if record.get(field):
                score += 1
        return score

    matched.sort(key=lambda r: (-_score(r), r.get("brand", ""), r.get("manufacturer_part_number", "")))
    return matched[:limit]
