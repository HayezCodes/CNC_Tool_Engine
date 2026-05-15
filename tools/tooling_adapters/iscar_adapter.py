"""Iscar structured JSON adapter for the Enterprise Tooling Search system.

Parses Iscar-style structured JSON tooling records into normalized tooling
search records matching grade_engine.tooling_search.SCHEMA_FIELDS.

Input format: JSON object with a catalog_header and a list of tool_records.
Each tool_record is a flat dict with Iscar-convention field names.

Iscar-specific notes:
  - chip_former: Iscar uses chip former codes (F3P, NF, etc.) which map to
    the schema's chipbreaker field.
  - High-feed milling inserts (HighFeedMillingInsert tool_type) are mapped
    to tool_category 'high_feed_insert' to distinguish them from general
    milling inserts in search and filter workflows.
  - Indexable drill systems (SUMOCHAM) include both body and replaceable tip —
    records represent the tip/platform, not assembled dimensions.
  - Boring bars are toolholders that accept indexable inserts; recorded as
    'boring_bar' to preserve that distinction from the insert itself.

Scope (safe subset only):
  - Identity: brand (always Iscar Ltd.), tool_category, series,
    family_name, designation, manufacturer_part_number
  - Technical: grade, chipbreaker (from chip_former), coating, material_fit,
    operation_fit, geometry_tags, holder_compatibility, coolant_capability
  - Source traceability: source_label, source_url, source_page_reference,
    verification_status, cutting_data_status, notes
  - Dimensions: always {} — never imported

Out of scope (enforced):
  - Any JSON key containing feed, speed, sfm, rpm, ipr, ipm, vc, or fz
    causes the entire record to be rejected.
  - cutting_data_status is always 'not_imported'.
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


BRAND = "Iscar Ltd."

# ── Tool category mapping ─────────────────────────────────────────────────────

_TOOL_CATEGORY_MAP: dict[str, str] = {
    "turninginsert": "turning_insert",
    "indexableturninginsert": "turning_insert",
    "millinginsert": "milling_insert",
    "indexablemillinginsert": "milling_insert",
    "facemillinginsert": "milling_insert",
    "shouldermillinginsert": "milling_insert",
    "helimillinsert": "milling_insert",
    "highfeedmillinginsert": "high_feed_insert",
    "highfeedinsert": "high_feed_insert",
    "indexabledrill": "indexable_drill",
    "drillinsert": "indexable_drill",
    "groovingtinsert": "grooving_insert",
    "groovinginsert": "grooving_insert",
    "partinginsert": "grooving_insert",
    "threadinginsert": "threading_insert",
    "boringbar": "boring_bar",
    "boringtoolholder": "boring_bar",
    "endmill": "endmill",
    "solidcarbideendmill": "endmill",
    "chamfermill": "chamfer_mill",
}

# ── Operation mapping ─────────────────────────────────────────────────────────

_OPERATION_MAP: dict[str, str] = {
    "externalturning": "external_turning",
    "internalturning": "internal_turning",
    "facing": "facing",
    "profiling": "profiling",
    "roughing": "roughing",
    "finishing": "finishing",
    "mediumturning": "medium_turning",
    "lightturning": "light_turning",
    "heavyturning": "heavy_turning",
    "drilling": "drilling",
    "throughholedrilling": "through_hole_drilling",
    "blindholedrilling": "blind_hole_drilling",
    "highefficiencydrilling": "high_efficiency_drilling",
    "generalmilling": "general_milling",
    "shouldermilling": "shoulder_milling",
    "facemilling": "face_milling",
    "slotmilling": "slot_milling",
    "ramping": "ramping",
    "plunging": "plunge_milling",
    "plungemilling": "plunge_milling",
    "highfeedmilling": "high_feed_milling",
    "trochoidal": "trochoidal_milling",
    "dynamicmilling": "dynamic_milling",
    "grooving": "grooving",
    "facegrooving": "face_grooving",
    "parting": "parting",
    "circulargrooving": "circular_grooving",
    "externalthreading": "external_threading",
    "internalthreading": "internal_threading",
    "boring": "boring",
}

# ── Coolant mapping ───────────────────────────────────────────────────────────

_COOLANT_MAP: dict[str, str] = {
    "throughcoolantcapable": "through_coolant_capable",
    "externalonly": "external_only",
    "unknown": "unknown",
    "verifybycatalog": "verify_by_catalog",
    "notapplicable": "unknown",
    "dry": "external_only",
    "": "unknown",
}


# ── Iscar adapter ─────────────────────────────────────────────────────────────

class IscarAdapter(BaseToolingAdapter):
    """Parse Iscar-style structured JSON tooling records into normalized records.

    Input: a JSON object with keys:
      - catalog_header.manufacturer
      - catalog_header.catalog_label
      - catalog_header.catalog_url
      - tool_records: list of tool record dicts

    Iscar uses 'chip_former' as the field name for what the schema calls
    'chipbreaker'.  The adapter maps chip_former → chipbreaker transparently.

    Usage::

        adapter = IscarAdapter()
        records = adapter.parse(Path("sample.json"))
        if adapter.parse_errors:
            print("Errors:", adapter.parse_errors)
        errors = adapter.validate_output(records)
    """

    SOURCE_FORMAT = "iscar_json"

    def parse(self, source: str | Path) -> list[dict[str, Any]]:
        """Parse an Iscar structured JSON file and return normalized records."""
        self._errors = []
        self._rejected_count = 0
        raw = Path(source).read_text(encoding="utf-8")
        return self.parse_json_string(raw)

    def parse_json_string(self, json_string: str) -> list[dict[str, Any]]:
        """Parse an Iscar JSON string and return normalized tooling records.

        Useful for testing with inline JSON. Resets parse_errors and rejected_count.
        """
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
                self._errors.append("Each tool_record must be a JSON object; skipping non-object entry.")
                self._rejected_count += 1
                continue

            record, error = self._normalize_record(
                raw_record,
                manufacturer=manufacturer,
                source_label=source_label,
                source_url=source_url,
            )
            if error:
                self._errors.append(error)
                self._rejected_count += 1
            elif record is not None:
                records.append(record)

        return records

    # ── Private helpers ───────────────────────────────────────────────────────

    def _normalize_record(
        self,
        raw: dict[str, Any],
        *,
        manufacturer: str,
        source_label: str,
        source_url: str,
    ) -> tuple[dict[str, Any] | None, str | None]:
        """Normalize one raw tool_record dict into a schema record."""
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
        # chip_former is Iscar's term for what the schema calls chipbreaker
        record["chipbreaker"] = str(raw.get("chip_former", raw.get("chipbreaker", ""))).strip()
        record["coating"] = str(raw.get("coating", "")).strip()

        raw_materials = raw.get("material_groups", [])
        if isinstance(raw_materials, list):
            record["material_fit"] = normalize_material_fit(raw_materials)

        raw_ops = raw.get("operations", [])
        if isinstance(raw_ops, list):
            record["operation_fit"] = self._map_operations(raw_ops)

        raw_tags = raw.get("geometry_tags", [])
        if isinstance(raw_tags, list):
            record["geometry_tags"] = normalize_geometry_tags(raw_tags)

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
        # dimensions always {}

        return record, None

    def _map_tool_category(self, raw: str) -> str:
        key = normalize_tool_category_value(raw)
        return _TOOL_CATEGORY_MAP.get(key, key)

    def _map_operations(self, raw_ops: list[str]) -> list[str]:
        result: list[str] = []
        for op in raw_ops:
            key = normalize_tool_category_value(op)
            result.append(_OPERATION_MAP.get(key, normalize_operation_fit([op])[0] if op.strip() else ""))
        return [op for op in result if op]

    def _map_coolant(self, raw: str) -> str:
        key = normalize_tool_category_value(raw)
        return _COOLANT_MAP.get(key, "unknown")


# ── Module-level convenience function ────────────────────────────────────────

def parse_iscar_file(source: str | Path) -> dict[str, Any]:
    """Parse an Iscar structured JSON file and return a result summary dict.

    Returns::

        {
            "source_file": str,
            "record_count": int,
            "rejected_count": int,
            "parse_errors": list[str],
            "validation_errors": list[str],
            "records": list[dict],
        }
    """
    adapter = IscarAdapter()
    records = adapter.parse(source)
    validation_errors = adapter.validate_output(records)
    return {
        "source_file": str(source),
        "record_count": len(records),
        "rejected_count": adapter.rejected_count,
        "parse_errors": adapter.parse_errors,
        "validation_errors": validation_errors,
        "records": records,
    }
