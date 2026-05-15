"""GTC / ISO 13399 XML adapter for the Enterprise Tooling Search system.

Parses a simplified GTC-style XML file (Generic Tool Catalog, co-developed by
Sandvik Coromant, Kennametal, Iscar, and Siemens, built on ISO 13399) into
normalized tooling search records matching grade_engine.tooling_search.SCHEMA_FIELDS.

Scope (safe subset only):
  - Identity fields: brand, manufacturer_part_number, tool_category, series,
    family_name, designation
  - Technical descriptors: grade, chipbreaker, coating, material_fit,
    operation_fit, geometry_tags, holder_compatibility, coolant_capability
  - Source traceability: source_label, source_url, source_page_reference,
    verification_status, cutting_data_status, notes
  - Dimensions: always set to {} — dimensions are NOT imported

Out of scope (enforced, not optional):
  - Feeds, speeds, sfm, rpm, ipr, ipm, vc, fz — any record or element
    containing these terms is rejected before output is produced.
  - Actual catalog dimensions — dimensions field is always empty dict.
  - Cutting data of any kind — cutting_data_status is always 'not_imported'.
"""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
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


# ── Tool category mapping  ────────────────────────────────────────────────────
# Maps GTC XML ToolCategory values (normalized to lowercase, no spaces) to our
# tooling search schema tool_category values.

_TOOL_CATEGORY_MAP: dict[str, str] = {
    "turninginsert": "turning_insert",
    "indexableturninginsert": "turning_insert",
    "millinginsert": "milling_insert",
    "indexablemillinginsert": "milling_insert",
    "facemillinginsert": "milling_insert",
    "shouldermillinginsert": "milling_insert",
    "endmill": "endmill",
    "solidendmill": "endmill",
    "solidcarbideendmill": "endmill",
    "solidcarbidedrill": "drill",
    "drill": "drill",
    "indexabledrill": "indexable_drill",
    "groovinginsert": "grooving_insert",
    "grooving": "grooving_insert",
    "partinginsert": "grooving_insert",
    "threadinginsert": "threading_insert",
    "threading": "threading_insert",
    "boringbar": "boring_bar",
    "chamfermill": "chamfer_mill",
    "burnishingtool": "burnishing_tool",
}


# ── Operation mapping ─────────────────────────────────────────────────────────
# Maps GTC XML Operation values (normalized) to our snake_case operation tags.
# Unknown operations fall back to normalize_operation_fit (passthrough).

_OPERATION_MAP: dict[str, str] = {
    "externalturning": "external_turning",
    "internalturning": "internal_turning",
    "facing": "facing",
    "profiling": "profiling",
    "roughing": "roughing",
    "finishing": "finishing",
    "mediumturning": "medium_turning",
    "lightturning": "light_turning",
    "drilling": "drilling",
    "throughholedrilling": "through_hole_drilling",
    "blindholedrilling": "blind_hole_drilling",
    "highefficiencydrilling": "high_efficiency_drilling",
    "generalmilling": "general_milling",
    "shouldermilling": "shoulder_milling",
    "facemilling": "face_milling",
    "slotmilling": "slot_milling",
    "ramping": "ramping",
    "plungemilling": "plunge_milling",
    "grooving": "grooving",
    "facegrooving": "face_grooving",
    "parting": "parting",
    "threading": "threading",
    "externalthreading": "external_threading",
    "internalthreading": "internal_threading",
    "boring": "boring",
    "smallbore": "small_bore",
    "smallcomponents": "small_components",
    "rapidmaterialremoval": "rapid_material_removal",
    "nonferrousmilling": "non_ferrous_milling",
}


# ── Coolant capability mapping ────────────────────────────────────────────────

_COOLANT_MAP: dict[str, str] = {
    "throughcoolantcapable": "through_coolant_capable",
    "externalonly": "external_only",
    "unknown": "unknown",
    "verifybycatalog": "verify_by_catalog",
    "notapplicable": "unknown",
    "dry": "external_only",
}


# ── GTC adapter implementation ────────────────────────────────────────────────

class GtcIso13399Adapter(BaseToolingAdapter):
    """Parse simplified GTC/ISO 13399 XML files into normalized tooling records.

    Usage::

        adapter = GtcIso13399Adapter()
        records = adapter.parse(Path("sample.xml"))
        if adapter.parse_errors:
            print("Errors:", adapter.parse_errors)
        validation_errors = adapter.validate_output(records)
    """

    SOURCE_FORMAT = "gtc_iso13399_xml"

    def parse(self, source: str | Path) -> list[dict[str, Any]]:
        """Parse a GTC/ISO 13399 XML file and return normalized tooling records.

        Records containing forbidden feed/speed element names are rejected.
        Rejection notices are stored in self.parse_errors.
        The output list contains only accepted, normalized records.
        """
        self._errors = []
        self._rejected_count = 0
        xml_text = Path(source).read_text(encoding="utf-8")
        return self.parse_xml_string(xml_text)

    def parse_xml_string(self, xml_string: str) -> list[dict[str, Any]]:
        """Parse a GTC/ISO 13399 XML string and return normalized tooling records.

        Useful for testing with inline XML. Resets parse_errors and rejected_count.
        """
        self._errors = []
        self._rejected_count = 0

        try:
            root = ET.fromstring(xml_string)
        except ET.ParseError as exc:
            self._errors.append(f"XML parse error: {exc}")
            return []

        header = root.find("CatalogHeader")
        manufacturer_name = _get_text(header, "ManufacturerName")
        source_label = _get_text(header, "CatalogLabel")
        source_url = _get_text(header, "CatalogURL")

        records: list[dict[str, Any]] = []
        items_container = root.find("ToolItems")
        if items_container is None:
            self._errors.append("No <ToolItems> element found in XML.")
            return records

        for item in items_container.findall("ToolItem"):
            record, error = self._parse_tool_item(
                item,
                manufacturer_name=manufacturer_name,
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

    def _parse_tool_item(
        self,
        item: ET.Element,
        *,
        manufacturer_name: str,
        source_label: str,
        source_url: str,
    ) -> tuple[dict[str, Any] | None, str | None]:
        """Parse one <ToolItem> element into a normalized record.

        Returns (record, None) on success or (None, error_message) on rejection.
        Rejection happens if any child element tag contains a forbidden feed/speed term.
        """
        mpn = item.findtext("MPN", "").strip()

        # Guard: reject records with forbidden element names
        for child in item:
            if field_contains_forbidden_term(child.tag):
                msg = (
                    f"Record '{mpn or 'unknown'}': rejected — "
                    f"forbidden element <{child.tag}> detected (feed/speed data not allowed)"
                )
                return None, msg

        record = make_empty_record()
        record["brand"] = manufacturer_name
        record["manufacturer_part_number"] = mpn
        record["tool_category"] = self._map_tool_category(item.findtext("ToolCategory", ""))
        record["series"] = item.findtext("Series", "").strip()
        record["family_name"] = item.findtext("FamilyName", "").strip()
        record["designation"] = item.findtext("Designation", "").strip()
        record["grade"] = item.findtext("Grade", "").strip()
        record["chipbreaker"] = item.findtext("Chipbreaker", "").strip()
        record["coating"] = item.findtext("Coating", "").strip()

        # List fields
        mg_container = item.find("MaterialGroups")
        if mg_container is not None:
            raw = [e.text.strip() for e in mg_container.findall("MaterialGroup") if e.text]
            record["material_fit"] = normalize_material_fit(raw)

        ops_container = item.find("Operations")
        if ops_container is not None:
            raw_ops = [e.text.strip() for e in ops_container.findall("Operation") if e.text]
            record["operation_fit"] = self._map_operations(raw_ops)

        gt_container = item.find("GeometryTags")
        if gt_container is not None:
            raw_tags = [e.text.strip() for e in gt_container.findall("GeometryTag") if e.text]
            record["geometry_tags"] = normalize_geometry_tags(raw_tags)

        holder_text = item.findtext("HolderCompatibility", "").strip()
        if holder_text:
            record["holder_compatibility"] = normalize_holder_compatibility(
                [h.strip() for h in holder_text.split(",")]
            )

        record["coolant_capability"] = self._map_coolant(
            item.findtext("CoolantCapability", "unknown")
        )

        # Source traceability
        record["source_label"] = source_label
        record["source_url"] = source_url
        record["source_page_reference"] = item.findtext("SourcePageReference", "").strip()

        # Always enforce safe defaults — never overridden by XML content
        record["verification_status"] = DEFAULT_VERIFICATION_STATUS
        record["cutting_data_status"] = DEFAULT_CUTTING_DATA_STATUS

        record["notes"] = item.findtext("Notes", "").strip()
        # dimensions intentionally left as {} — never import from XML

        return record, None

    def _map_tool_category(self, raw: str) -> str:
        key = normalize_tool_category_value(raw)
        return _TOOL_CATEGORY_MAP.get(key, key)

    def _map_operations(self, raw_ops: list[str]) -> list[str]:
        result: list[str] = []
        for op in raw_ops:
            key = normalize_tool_category_value(op)
            result.append(_OPERATION_MAP.get(key, key))
        return [op for op in result if op]

    def _map_coolant(self, raw: str) -> str:
        key = normalize_tool_category_value(raw)
        return _COOLANT_MAP.get(key, "unknown")


# ── Module-level convenience functions ───────────────────────────────────────

def parse_gtc_file(source: str | Path) -> dict[str, Any]:
    """Parse a GTC/ISO 13399 XML file and return a result summary dict.

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
    adapter = GtcIso13399Adapter()
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


# ── Internal XML helper ───────────────────────────────────────────────────────

def _get_text(element: ET.Element | None, tag: str, default: str = "") -> str:
    """Safely get text from a child element; returns default if missing."""
    if element is None:
        return default
    child = element.find(tag)
    if child is None or child.text is None:
        return default
    return child.text.strip()
