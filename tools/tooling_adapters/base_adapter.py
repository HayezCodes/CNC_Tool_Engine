"""Base adapter utilities and contract for manufacturer tooling data format adapters.

Adapters parse manufacturer-specific file formats (GTC XML, P21, DIN 4000 XML, etc.)
and produce normalized tooling search records that match the schema defined in
grade_engine.tooling_search.SCHEMA_FIELDS.

Adapter output must go through the existing audit/review workflow before entering
the tooling search records directory. Adapters never write directly to records/.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

# Allow import regardless of working directory
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from grade_engine.tooling_search import SCHEMA_FIELDS, normalize_tool_query


# ── Constants shared across all adapters ─────────────────────────────────────

FORBIDDEN_FIELD_TERMS: tuple[str, ...] = (
    "feed", "speed", "sfm", "rpm", "ipr", "ipm", "vc", "fz",
)

VALID_VERIFICATION_STATUSES: frozenset[str] = frozenset({
    "verified_source_page_record",
    "sample_family_level_not_catalog_verified",
    "reviewed_exact_tool_candidate",
    "reviewed_family_level_candidate",
})

VALID_CUTTING_DATA_STATUSES: frozenset[str] = frozenset({
    "not_imported",
})

ISO_MATERIAL_GROUPS: frozenset[str] = frozenset({"P", "M", "K", "N", "S", "H"})

# Field names in the output record that must be lists
LIST_FIELDS: frozenset[str] = frozenset({
    "material_fit", "operation_fit", "geometry_tags", "holder_compatibility",
})

# Safe default verification / cutting-data status for all adapter output
DEFAULT_VERIFICATION_STATUS = "sample_family_level_not_catalog_verified"
DEFAULT_CUTTING_DATA_STATUS = "not_imported"


# ── Forbidden-field detection ─────────────────────────────────────────────────

def field_contains_forbidden_term(field_name: str) -> bool:
    """Return True if the field name (key or XML element tag) contains a
    forbidden feed/speed term after normalization.

    Matches feed, speed, sfm, rpm, ipr, ipm, vc, fz as substrings of the
    normalized name. Used to guard both output JSON keys and source XML tags.
    """
    lowered = normalize_tool_query(str(field_name))
    return any(term in lowered for term in FORBIDDEN_FIELD_TERMS)


# ── List normalization helpers ────────────────────────────────────────────────

def normalize_material_fit(values: list[str]) -> list[str]:
    """Validate and return only recognized ISO material group codes."""
    return [str(v).strip().upper() for v in values
            if str(v).strip().upper() in ISO_MATERIAL_GROUPS]


def normalize_operation_fit(values: list[str]) -> list[str]:
    """Normalize operation labels to lowercase snake_case strings."""
    result: list[str] = []
    for v in values:
        normalized = normalize_tool_query(str(v)).replace(" ", "_")
        if normalized:
            result.append(normalized)
    return result


def normalize_geometry_tags(values: list[str]) -> list[str]:
    """Normalize geometry tag labels to lowercase snake_case strings."""
    return normalize_operation_fit(values)


def normalize_holder_compatibility(values: list[str]) -> list[str]:
    """Return plain stripped holder compatibility strings."""
    return [str(v).strip() for v in values if str(v).strip()]


def normalize_tool_category_value(value: str) -> str:
    """Normalize a tool category value to lowercase snake_case."""
    return normalize_tool_query(str(value)).replace(" ", "_")


# ── Source metadata helpers ───────────────────────────────────────────────────

def make_source_metadata(
    *,
    source_label: str,
    source_url: str,
    source_page_reference: str = "",
    verification_status: str = DEFAULT_VERIFICATION_STATUS,
    cutting_data_status: str = DEFAULT_CUTTING_DATA_STATUS,
) -> dict[str, str]:
    """Build a source-metadata dict fragment for a normalized record.

    Always sets cutting_data_status = 'not_imported'.
    Verification status defaults to sample_family_level_not_catalog_verified.
    """
    return {
        "source_label": str(source_label).strip(),
        "source_url": str(source_url).strip(),
        "source_page_reference": str(source_page_reference).strip(),
        "verification_status": verification_status,
        "cutting_data_status": "not_imported",  # enforced regardless of argument
    }


# ── Empty record factory ──────────────────────────────────────────────────────

def make_empty_record() -> dict[str, Any]:
    """Return a fresh dict with all schema fields set to safe empty defaults.

    Guarantees the record has every field in SCHEMA_FIELDS so downstream
    validation does not report missing fields.
    """
    return {
        "brand": "",
        "tool_category": "",
        "manufacturer_part_number": "",
        "series": "",
        "family_name": "",
        "designation": "",
        "grade": "",
        "chipbreaker": "",
        "coating": "",
        "material_fit": [],
        "operation_fit": [],
        "geometry_tags": [],
        "dimensions": {},
        "holder_compatibility": [],
        "coolant_capability": "unknown",
        "source_label": "",
        "source_url": "",
        "source_page_reference": "",
        "verification_status": DEFAULT_VERIFICATION_STATUS,
        "cutting_data_status": DEFAULT_CUTTING_DATA_STATUS,
        "notes": "",
    }


# ── Output validation ─────────────────────────────────────────────────────────

def validate_adapter_output(records: list[dict[str, Any]]) -> list[str]:
    """Validate a list of adapter-produced records against the schema contract.

    Returns a list of error strings (empty means all records pass).
    Does NOT write, modify, or import anything.
    """
    errors: list[str] = []

    for idx, record in enumerate(records):
        label = record.get("manufacturer_part_number") or f"record_{idx}"

        # Every schema field must be present
        missing = [f for f in SCHEMA_FIELDS if f not in record]
        if missing:
            errors.append(f"{label}: missing schema fields: {', '.join(missing)}")

        # Output keys must not contain forbidden feed/speed terms
        bad_keys = sorted(k for k in record if field_contains_forbidden_term(str(k)))
        if bad_keys:
            errors.append(
                f"{label}: forbidden feed/speed field names in output: {', '.join(bad_keys)}"
            )

        # cutting_data_status must be not_imported
        cds = str(record.get("cutting_data_status", "")).strip()
        if cds != "not_imported":
            errors.append(
                f"{label}: cutting_data_status must be 'not_imported', got '{cds}'"
            )

        # verification_status must be a valid value
        vs = str(record.get("verification_status", "")).strip()
        if vs not in VALID_VERIFICATION_STATUSES:
            errors.append(f"{label}: invalid verification_status '{vs}'")

        # List fields must actually be lists
        for list_field in LIST_FIELDS:
            val = record.get(list_field)
            if val is not None and not isinstance(val, list):
                errors.append(f"{label}: '{list_field}' must be a list, got {type(val).__name__}")

        # dimensions must be a dict
        dims = record.get("dimensions")
        if dims is not None and not isinstance(dims, dict):
            errors.append(f"{label}: 'dimensions' must be a dict, got {type(dims).__name__}")

    return errors


# ── Base adapter class ────────────────────────────────────────────────────────

class BaseToolingAdapter:
    """Abstract base class for manufacturer tooling data format adapters.

    Subclasses implement parse() (and optionally parse_xml_string()) to convert
    manufacturer-specific source data into normalized tooling search records.

    Adapter output must pass validate_adapter_output() before downstream use.
    Records must then go through the audit / review workflow — adapters do NOT
    write directly to tool_data/tooling_search/records/.
    """

    SOURCE_FORMAT: str = "unknown"

    # Populated by parse() implementations
    _errors: list[str]
    _rejected_count: int

    def __init__(self) -> None:
        self._errors = []
        self._rejected_count = 0

    def parse(self, source: Any) -> list[dict[str, Any]]:
        """Parse source data and return normalized tooling records.

        Subclasses must override this method.
        Errors encountered during parsing are stored in self.parse_errors.
        """
        raise NotImplementedError(f"{type(self).__name__}.parse() must be implemented")

    @property
    def parse_errors(self) -> list[str]:
        """Errors and rejected-record notices from the most recent parse() call."""
        return list(self._errors)

    @property
    def rejected_count(self) -> int:
        """Number of records rejected during the most recent parse() call."""
        return self._rejected_count

    def validate_output(self, records: list[dict[str, Any]]) -> list[str]:
        """Validate adapter output against the tooling search schema contract."""
        return validate_adapter_output(records)

    def make_empty_record(self) -> dict[str, Any]:
        """Return a fresh empty record with all schema fields and safe defaults."""
        return make_empty_record()
