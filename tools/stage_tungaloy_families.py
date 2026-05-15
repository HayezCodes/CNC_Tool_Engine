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


OUTPUT_FILENAME = "tungaloy_multifunction_families.json"
REVIEW_NOTE = "Family-level staged data needs human catalog review before production use."

FAMILY_SPECS = [
    {
        "tool_category": "grooving_insert",
        "family_name": "Grooving and parting insert families",
        "operation_fit": ["grooving", "parting", "face_grooving", "profiling"],
        "material_fit": ["P", "M", "K", "N", "S"],
        "strategy_fit": ["grooving", "production_turning", "insert_grade_verification_required"],
        "coating_or_grade": "verify groove insert grade families and system platforms by catalog",
        "geometry_tags": ["grooving_insert", "groove_form_requires_review", "grade_family_requires_review"],
        "dimension_summary": "family-level grooving insert category only; verify groove form, insert style, system platform, and target materials by catalog",
    },
    {
        "tool_category": "grooving_toolholder",
        "family_name": "Grooving and parting holder families",
        "operation_fit": ["grooving", "parting", "face_grooving"],
        "material_fit": ["P", "M", "K", "N", "S"],
        "strategy_fit": ["grooving", "tooling_system", "manual_catalog_review_required"],
        "coating_or_grade": "verify compatible insert systems and holder style by catalog",
        "geometry_tags": ["grooving_toolholder", "system_platform", "insert_compatibility_requires_review"],
        "dimension_summary": "family-level grooving holder category only; verify holder style, hand, insert family compatibility, and application limits by catalog",
    },
    {
        "tool_category": "threading_insert",
        "family_name": "Threading insert families",
        "operation_fit": ["threading", "external_threading", "internal_threading"],
        "material_fit": ["P", "M", "K", "N", "S"],
        "strategy_fit": ["threading", "production_turning", "manual_catalog_review_required"],
        "coating_or_grade": "verify thread form, pitch grouping, and grade family by catalog",
        "geometry_tags": ["threading_insert", "thread_form_requires_review", "grade_family_requires_review"],
        "dimension_summary": "family-level threading insert category only; verify thread form, pitch grouping, insert style, and holder compatibility by catalog",
    },
    {
        "tool_category": "threading_toolholder",
        "family_name": "Threading holder families",
        "operation_fit": ["threading", "external_threading", "internal_threading"],
        "material_fit": ["P", "M", "K", "N", "S"],
        "strategy_fit": ["threading", "tooling_system", "manual_catalog_review_required"],
        "coating_or_grade": "verify compatible insert systems and holder style by catalog",
        "geometry_tags": ["threading_toolholder", "system_platform", "insert_compatibility_requires_review"],
        "dimension_summary": "family-level threading holder category only; verify holder style, hand, insert family compatibility, and application limits by catalog",
    },
    {
        "tool_category": "indexable_cutter",
        "family_name": "High-feed milling cutter families",
        "operation_fit": ["high_feed_milling", "roughing", "face_milling", "shoulder_milling"],
        "material_fit": ["P", "M", "K", "N", "S"],
        "strategy_fit": ["high_feed", "production_milling", "insert_grade_verification_required"],
        "coating_or_grade": "verify high-feed insert grades and cutter systems by catalog",
        "geometry_tags": ["indexable_cutter", "high_feed", "system_platform"],
        "dimension_summary": "family-level high-feed milling cutter category only; verify cutter platform, insert family, entering angle, and target operations by catalog",
    },
    {
        "tool_category": "multifunction_tooling",
        "family_name": "Multifunction turning and milling system families",
        "operation_fit": ["grooving", "threading", "turning", "specialty_milling"],
        "material_fit": ["P", "M", "K", "N", "S", "H"],
        "strategy_fit": ["multifunction", "tooling_system", "manual_catalog_review_required"],
        "coating_or_grade": "verify platform compatibility and insert families by catalog",
        "geometry_tags": ["multifunction_tooling", "system_platform", "insert_compatibility_requires_review"],
        "dimension_summary": "family-level multifunction tooling category only; verify system platform, compatible inserts, operation limits, and machine-side requirements by catalog",
    },
]


def build_tungaloy_family_records() -> list[dict]:
    source = _tungaloy_source()
    return [
        build_staged_record(
            brand="Tungaloy",
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


def stage_tungaloy_family_records() -> int:
    records = build_tungaloy_family_records()
    errors = _validation_errors(records)
    if errors:
        raise ValueError("; ".join(errors))
    save_staged_records(
        "Tungaloy",
        records,
        output_filename=OUTPUT_FILENAME,
    )
    return len(records)


def _tungaloy_source() -> dict:
    matches = list_sources_by_brand("Tungaloy")
    if not matches:
        raise ValueError("Tungaloy source is not registered in catalog_sources.json.")
    return matches[0]


def _validation_errors(records: list[dict]) -> list[str]:
    errors: list[str] = []
    for index, record in enumerate(records):
        errors.extend(f"record {index}: {error}" for error in validate_staged_record(record))
    return errors


if __name__ == "__main__":
    count = stage_tungaloy_family_records()
    print(f"Saved {count} staged Tungaloy family records.")
