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


OUTPUT_FILENAME = "micro_100_turning_families.json"
REVIEW_NOTE = "Family-level staged data needs human catalog review before production use."

FAMILY_SPECS = [
    {
        "tool_category": "boring_bar",
        "family_name": "Solid carbide boring bar families",
        "operation_fit": ["boring", "internal_turning", "small_id_turning", "profiling"],
        "material_fit": ["P", "M", "K", "N", "S", "H"],
        "strategy_fit": ["small_id_access", "rigidity_priority", "manual_catalog_review_required"],
        "coating_or_grade": "verify carbide substrate and coating family by catalog",
        "geometry_tags": ["boring_bar", "solid_carbide", "small_id_candidate"],
        "dimension_summary": "family-level solid carbide boring bar category only; verify shank style, minimum bore, reach, hand, and insert/form details by catalog",
    },
    {
        "tool_category": "boring_bar",
        "family_name": "Indexable boring bar families",
        "operation_fit": ["boring", "internal_turning", "shoulder_turning", "small_id_turning"],
        "material_fit": ["P", "M", "K", "N", "S", "H"],
        "strategy_fit": ["indexable_turning", "small_id_access", "production_turning"],
        "coating_or_grade": "verify insert compatibility and holder style by catalog",
        "geometry_tags": ["boring_bar", "indexable", "small_id_candidate"],
        "dimension_summary": "family-level indexable boring bar category only; verify insert style, shank size, bore range, hand, and reach by catalog",
    },
    {
        "tool_category": "miniature_turning_tool",
        "family_name": "Miniature internal turning tool families",
        "operation_fit": ["internal_turning", "profiling", "facing", "small_feature_turning"],
        "material_fit": ["P", "M", "K", "N", "S", "H"],
        "strategy_fit": ["miniature_work", "small_feature_access", "manual_catalog_review_required"],
        "coating_or_grade": "verify solid carbide, brazed, or insert style by catalog",
        "geometry_tags": ["miniature_turning", "small_id_candidate", "clearance_requires_review"],
        "dimension_summary": "family-level miniature internal turning category only; verify minimum bore, hand, reach, nose form, and application limits by catalog",
    },
    {
        "tool_category": "grooving_tool",
        "family_name": "Internal grooving tool families",
        "operation_fit": ["internal_grooving", "grooving", "face_grooving", "profiling"],
        "material_fit": ["P", "M", "K", "N", "S", "H"],
        "strategy_fit": ["grooving", "small_id_access", "manual_catalog_review_required"],
        "coating_or_grade": "verify insert or form style by catalog",
        "geometry_tags": ["internal_grooving", "small_id_candidate", "groove_form_requires_review"],
        "dimension_summary": "family-level internal grooving category only; verify groove style, minimum bore, insert/form width range, and reach by catalog",
    },
    {
        "tool_category": "threading_tool",
        "family_name": "Miniature internal threading tool families",
        "operation_fit": ["internal_threading", "threading", "small_feature_turning"],
        "material_fit": ["P", "M", "K", "N", "S", "H"],
        "strategy_fit": ["threading", "small_id_access", "manual_catalog_review_required"],
        "coating_or_grade": "verify thread form and holder style by catalog",
        "geometry_tags": ["internal_threading", "small_id_candidate", "thread_form_requires_review"],
        "dimension_summary": "family-level miniature internal threading category only; verify thread form, pitch range, bore access, hand, and reach by catalog",
    },
    {
        "tool_category": "specialty_turning",
        "family_name": "Small-ID multifunction turning tool families",
        "operation_fit": ["small_feature_turning", "grooving", "profiling", "specialty_turning"],
        "material_fit": ["P", "M", "K", "N", "S", "H"],
        "strategy_fit": ["multifunction", "small_id_access", "manual_catalog_review_required"],
        "coating_or_grade": "verify geometry family and substrate by catalog",
        "geometry_tags": ["specialty_turning", "multifunction_candidate", "small_id_candidate"],
        "dimension_summary": "family-level multifunction small-ID turning category only; verify exact form, groove/thread compatibility, bore access, and application limits by catalog",
    },
]


def build_micro_100_family_records() -> list[dict]:
    source = _micro_100_source()
    return [
        build_staged_record(
            brand="Micro 100",
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


def stage_micro_100_family_records() -> int:
    records = build_micro_100_family_records()
    errors = _validation_errors(records)
    if errors:
        raise ValueError("; ".join(errors))
    save_staged_records(
        "Micro 100",
        records,
        output_filename=OUTPUT_FILENAME,
    )
    return len(records)


def _micro_100_source() -> dict:
    matches = list_sources_by_brand("Micro 100")
    if not matches:
        raise ValueError("Micro 100 source is not registered in catalog_sources.json.")
    return matches[0]


def _validation_errors(records: list[dict]) -> list[str]:
    errors: list[str] = []
    for index, record in enumerate(records):
        errors.extend(f"record {index}: {error}" for error in validate_staged_record(record))
    return errors


if __name__ == "__main__":
    count = stage_micro_100_family_records()
    print(f"Saved {count} staged Micro 100 family records.")
