import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.catalog_ingestion import (  # noqa: E402
    build_staged_record,
    list_sources_by_brand,
    save_staged_records,
    validate_staged_record,
)


OUTPUT_FILENAME = "harvey_tool_specialty_families.json"
REVIEW_NOTE = "Family-level staged data needs human catalog review before production use."

FAMILY_SPECS = [
    {
        "tool_category": "chamfer_mill",
        "family_name": "Chamfer mill families",
        "operation_fit": ["chamfer", "deburring", "edge_breaking", "spotting"],
        "material_fit": ["P", "M", "K", "N", "S", "H"],
        "strategy_fit": ["specialty_milling", "edge_preparation", "manual_catalog_review_required"],
        "coating_or_grade": "verify coating family by catalog",
        "geometry_tags": ["chamfer_mill", "angle_geometry_requires_review", "specialty_cutter"],
        "dimension_summary": "family-level chamfer mill category only; verify angle, diameter, flute count, reach, and material application by catalog",
    },
    {
        "tool_category": "keyseat_cutter",
        "family_name": "Keyseat cutter families",
        "operation_fit": ["keyseat", "keyway", "slotting", "undercutting"],
        "material_fit": ["P", "M", "K", "N", "S", "H"],
        "strategy_fit": ["specialty_feature", "slotting", "manual_catalog_review_required"],
        "coating_or_grade": "verify coating family by catalog",
        "geometry_tags": ["keyseat_cutter", "slotting_candidate", "clearance_requires_review"],
        "dimension_summary": "family-level keyseat cutter category only; verify cutter width, diameter, neck clearance, reach, and arbor/shank details by catalog",
    },
    {
        "tool_category": "thread_mill",
        "family_name": "Thread mill families",
        "operation_fit": ["threading", "internal_threading", "external_threading", "thread_milling"],
        "material_fit": ["P", "M", "K", "N", "S", "H"],
        "strategy_fit": ["thread_milling", "specialty_feature", "manual_catalog_review_required"],
        "coating_or_grade": "verify coating family by catalog",
        "geometry_tags": ["thread_mill", "thread_form_requires_review", "solid_carbide"],
        "dimension_summary": "family-level thread mill category only; verify thread form, pitch range, cutter diameter, reach, and programming requirements by catalog",
    },
    {
        "tool_category": "miniature_endmill",
        "family_name": "Miniature end mill families",
        "operation_fit": ["miniature_milling", "small_feature_milling", "profiling", "finishing"],
        "material_fit": ["P", "M", "K", "N", "S", "H"],
        "strategy_fit": ["miniature_work", "small_feature_access", "manual_catalog_review_required"],
        "coating_or_grade": "verify coating family by catalog",
        "geometry_tags": ["miniature_endmill", "small_feature_candidate", "deflection_risk_requires_review"],
        "dimension_summary": "family-level miniature end mill category only; verify diameter, reach, flute count, neck clearance, and deflection risk by catalog",
    },
    {
        "tool_category": "undercut_tool",
        "family_name": "Undercutting tool families",
        "operation_fit": ["undercutting", "relief_milling", "back_chamfering", "specialty_milling"],
        "material_fit": ["P", "M", "K", "N", "S", "H"],
        "strategy_fit": ["specialty_feature", "clearance_priority", "manual_catalog_review_required"],
        "coating_or_grade": "verify coating family by catalog",
        "geometry_tags": ["undercut_tool", "clearance_requires_review", "specialty_cutter"],
        "dimension_summary": "family-level undercutting tool category only; verify cutter form, neck clearance, reach, shank clearance, and application limits by catalog",
    },
    {
        "tool_category": "specialty_milling",
        "family_name": "Specialty milling cutter families",
        "operation_fit": ["specialty_milling", "feature_milling", "profiling", "problem_solving"],
        "material_fit": ["P", "M", "K", "N", "S", "H"],
        "strategy_fit": ["specialty_feature", "problem_solving", "manual_catalog_review_required"],
        "coating_or_grade": "verify coating family by catalog",
        "geometry_tags": ["specialty_milling", "geometry_requires_review", "catalog_review_required"],
        "dimension_summary": "family-level specialty milling category only; verify exact cutter form, clearance, reach, coating, and application by catalog",
    },
]


def build_harvey_family_records() -> list[dict]:
    source = _harvey_source()
    return [
        build_staged_record(
            brand="Harvey Tool",
            source_label=source["source_label"],
            source_url=source["source_url"],
            source_type=source["source_type"],
            catalog_number="",
            cutting_data_status="not_imported",
            verification_status="staged_unreviewed",
            review_notes=REVIEW_NOTE,
            source_page_reference="",
            **spec,
        )
        for spec in FAMILY_SPECS
    ]


def stage_harvey_family_records() -> int:
    records = build_harvey_family_records()
    errors = _validation_errors(records)
    if errors:
        raise ValueError("; ".join(errors))
    save_staged_records(
        "Harvey Tool",
        records,
        output_filename=OUTPUT_FILENAME,
    )
    return len(records)


def _harvey_source() -> dict:
    matches = list_sources_by_brand("Harvey Tool")
    if not matches:
        raise ValueError("Harvey Tool source is not registered in catalog_sources.json.")
    return matches[0]


def _validation_errors(records: list[dict]) -> list[str]:
    errors: list[str] = []
    for index, record in enumerate(records):
        errors.extend(f"record {index}: {error}" for error in validate_staged_record(record))
    return errors


if __name__ == "__main__":
    count = stage_harvey_family_records()
    print(f"Saved {count} staged Harvey Tool specialty family records.")
