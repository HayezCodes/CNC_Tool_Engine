"""Niagara Cutter structured JSON adapter for the Enterprise Tooling Search system.

Niagara Cutter (part of Greenfield Industries) is a US cutting tool manufacturer.
Key product families: 4-flute square endmills, aluminum-specific endmills, high
performance endmills, roughing endmills, drills, reamers, thread mills, and taps.

Synthetic fixture adapter — not real catalog data.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools.tooling_adapters.base_adapter import (
    BaseToolingAdapter,
    DEFAULT_CUTTING_DATA_STATUS,
    DEFAULT_VERIFICATION_STATUS,
    field_contains_forbidden_term,
    make_empty_record,
    normalize_geometry_tags,
    normalize_holder_compatibility,
    normalize_material_fit,
    normalize_operation_fit,
    normalize_tool_category_value,
)

BRAND = "Niagara Cutter"

_TOOL_CATEGORY_MAP: dict[str, str] = {
    "solidcarbideendmill": "endmill",
    "endmill": "endmill",
    "solidcarbidedrill": "drill",
    "hssdrill": "drill",
    "spotdrill": "drill",
    "threadmill": "thread_mill",
    "solidcarbidethreadmill": "thread_mill",
    "reamer": "reamer",
    "solidcarbidereamer": "reamer",
    "spiraltap": "tap",
    "machinetap": "tap",
    "formtap": "tap",
    "carbidespiraltap": "tap",
    "countersink": "countersink",
    "stepdrill": "step_drill",
    "turninginsert": "turning_insert",
    "millinginsert": "milling_insert",
}

_OPERATION_MAP: dict[str, str] = {
    "generalmilling": "general_milling",
    "shouldermilling": "shoulder_milling",
    "slotmilling": "slot_milling",
    "ramping": "ramping",
    "plungemilling": "plunge_milling",
    "highfeedmilling": "high_feed_milling",
    "trochoidal": "trochoidal_milling",
    "dynamicmilling": "dynamic_milling",
    "finishing": "finishing",
    "roughing": "roughing",
    "profiling": "profiling",
    "drilling": "drilling",
    "throughholedrilling": "through_hole_drilling",
    "blindholedrilling": "blind_hole_drilling",
    "tapping": "tapping",
    "threadmilling": "thread_milling",
    "internalthreadmilling": "internal_thread_milling",
    "externalthreadmilling": "external_thread_milling",
    "reaming": "reaming",
    "countersinking": "countersinking",
    "chamfering": "chamfering",
}

_COOLANT_MAP: dict[str, str] = {
    "throughcoolantcapable": "through_coolant_capable",
    "externalonly": "external_only",
    "unknown": "unknown",
    "verifybycatalog": "verify_by_catalog",
    "flood": "external_only",
    "": "unknown",
}


class NiagaraCutterAdapter(BaseToolingAdapter):
    """Parse Niagara Cutter-style structured JSON tooling records into normalized records."""

    SOURCE_FORMAT = "niagara_cutter_json"

    def parse(self, source: str | Path) -> list[dict[str, Any]]:
        self._errors = []
        self._rejected_count = 0
        return self.parse_json_string(Path(source).read_text(encoding="utf-8"))

    def parse_json_string(self, json_string: str) -> list[dict[str, Any]]:
        self._errors = []
        self._rejected_count = 0
        try:
            data = json.loads(json_string)
        except json.JSONDecodeError as exc:
            self._errors.append(f"JSON parse error: {exc}")
            return []
        if not isinstance(data, dict):
            self._errors.append("Top-level JSON must be an object with catalog_header and tool_records.")
            return []
        header = data.get("catalog_header", {})
        manufacturer = str(header.get("manufacturer", BRAND)).strip() or BRAND
        source_label = str(header.get("catalog_label", "")).strip()
        source_url = str(header.get("catalog_url", "")).strip()
        tool_records = data.get("tool_records")
        if not isinstance(tool_records, list):
            self._errors.append("'tool_records' must be a JSON array.")
            return []
        records: list[dict[str, Any]] = []
        for raw_record in tool_records:
            if not isinstance(raw_record, dict):
                self._errors.append("Each tool_record must be a JSON object; skipping.")
                self._rejected_count += 1
                continue
            record, error = self._normalize_record(
                raw_record, manufacturer=manufacturer,
                source_label=source_label, source_url=source_url,
            )
            if error:
                self._errors.append(error)
                self._rejected_count += 1
            elif record is not None:
                records.append(record)
        return records

    def _normalize_record(self, raw, *, manufacturer, source_label, source_url):
        mpn = str(raw.get("part_number", "")).strip()
        for key in raw:
            if field_contains_forbidden_term(str(key)):
                return None, (
                    f"Record '{mpn or 'unknown'}': rejected — "
                    f"forbidden key '{key}' detected (feed/speed data not allowed)"
                )
        record = make_empty_record()
        record["brand"] = manufacturer
        record["manufacturer_part_number"] = mpn
        record["tool_category"] = self._map_tool_category(str(raw.get("tool_type", "")))
        record["series"] = str(raw.get("series", "")).strip()
        record["family_name"] = str(raw.get("family_name", "")).strip()
        record["designation"] = str(raw.get("designation", "")).strip()
        record["grade"] = str(raw.get("grade", "")).strip()
        record["chipbreaker"] = str(raw.get("chipbreaker", "")).strip()
        record["coating"] = str(raw.get("coating", "")).strip()
        if isinstance(raw.get("material_groups"), list):
            record["material_fit"] = normalize_material_fit(raw["material_groups"])
        if isinstance(raw.get("operations"), list):
            record["operation_fit"] = self._map_operations(raw["operations"])
        if isinstance(raw.get("geometry_tags"), list):
            record["geometry_tags"] = normalize_geometry_tags(raw["geometry_tags"])
        holder_raw = str(raw.get("holder_compatibility", "")).strip()
        if holder_raw:
            record["holder_compatibility"] = normalize_holder_compatibility(
                [h.strip() for h in holder_raw.split(",")]
            )
        record["coolant_capability"] = self._map_coolant(str(raw.get("coolant", "")))
        record["source_label"] = source_label
        record["source_url"] = source_url
        record["source_page_reference"] = str(raw.get("source_page", "")).strip()
        record["verification_status"] = DEFAULT_VERIFICATION_STATUS
        record["cutting_data_status"] = DEFAULT_CUTTING_DATA_STATUS
        record["notes"] = str(raw.get("notes", "")).strip()
        return record, None

    def _map_tool_category(self, raw: str) -> str:
        return _TOOL_CATEGORY_MAP.get(normalize_tool_category_value(raw), normalize_tool_category_value(raw))

    def _map_operations(self, raw_ops: list[str]) -> list[str]:
        result = []
        for op in raw_ops:
            key = normalize_tool_category_value(op)
            result.append(_OPERATION_MAP.get(key, normalize_operation_fit([op])[0] if op.strip() else ""))
        return [op for op in result if op]

    def _map_coolant(self, raw: str) -> str:
        return _COOLANT_MAP.get(normalize_tool_category_value(raw), "unknown")


def parse_niagara_cutter_file(source: str | Path) -> dict[str, Any]:
    """Parse a Niagara Cutter structured JSON file and return a result summary dict."""
    adapter = NiagaraCutterAdapter()
    records = adapter.parse(source)
    return {
        "source_file": str(source),
        "record_count": len(records),
        "rejected_count": adapter.rejected_count,
        "parse_errors": adapter.parse_errors,
        "validation_errors": adapter.validate_output(records),
        "records": records,
    }
