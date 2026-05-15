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


OUTPUT_FILENAME = "kyocera_indexable_families.json"
REVIEW_NOTE = "Family-level staged data needs human catalog review before production use."

FAMILY_SPECS = [
    {
        "tool_category": "turning_insert",
        "family_name": "General-purpose turning insert families",
        "operation_fit": ["external_turning", "internal_turning", "profiling", "facing"],
        "material_fit": ["P", "M", "K", "N", "S", "H"],
        "strategy_fit": ["general_purpose", "production_turning", "insert_grade_verification_required"],
        "coating_or_grade": "verify insert grade families and chipbreaker groups by catalog",
        "geometry_tags": ["turning_insert", "chipbreaker_requires_review", "grade_family_requires_review"],
        "dimension_summary": "family-level turning insert category only; verify shape, relief, chipbreaker family, grade family, and ISO application by catalog",
    },
    {
        "tool_category": "turning_insert",
        "family_name": "Finishing and profiling turning insert families",
        "operation_fit": ["finishing", "profiling", "facing", "copy_turning"],
        "material_fit": ["P", "M", "K", "N", "S"],
        "strategy_fit": ["finishing", "surface_finish_priority", "production_turning"],
        "coating_or_grade": "verify finishing grade families and chipbreaker groups by catalog",
        "geometry_tags": ["turning_insert", "finishing", "grade_family_requires_review"],
        "dimension_summary": "family-level finishing turning insert category only; verify nose style, chipbreaker family, grade family, and holder compatibility by catalog",
    },
    {
        "tool_category": "milling_insert",
        "family_name": "Shoulder milling insert families",
        "operation_fit": ["shoulder_milling", "face_milling", "slotting", "general_milling"],
        "material_fit": ["P", "M", "K", "N", "S", "H"],
        "strategy_fit": ["production_milling", "general_purpose", "insert_grade_verification_required"],
        "coating_or_grade": "verify milling insert grade families and cutter systems by catalog",
        "geometry_tags": ["milling_insert", "shoulder_milling", "grade_family_requires_review"],
        "dimension_summary": "family-level shoulder milling insert category only; verify insert style, cutter system, grade family, and application range by catalog",
    },
    {
        "tool_category": "milling_insert",
        "family_name": "Face milling insert families",
        "operation_fit": ["face_milling", "roughing", "finishing", "general_milling"],
        "material_fit": ["P", "M", "K", "N", "S"],
        "strategy_fit": ["production_milling", "face_milling", "insert_grade_verification_required"],
        "coating_or_grade": "verify face mill insert grade families and cutter systems by catalog",
        "geometry_tags": ["milling_insert", "face_milling", "grade_family_requires_review"],
        "dimension_summary": "family-level face milling insert category only; verify insert style, cutter system, grade family, and target materials by catalog",
    },
    {
        "tool_category": "grooving_insert",
        "family_name": "Grooving and cut-off insert families",
        "operation_fit": ["grooving", "parting", "face_grooving", "profiling"],
        "material_fit": ["P", "M", "K", "N", "S"],
        "strategy_fit": ["grooving", "production_turning", "insert_grade_verification_required"],
        "coating_or_grade": "verify groove insert grade families and system platforms by catalog",
        "geometry_tags": ["grooving_insert", "groove_form_requires_review", "grade_family_requires_review"],
        "dimension_summary": "family-level grooving insert category only; verify groove form, insert style, system platform, and target materials by catalog",
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
]


def build_kyocera_family_records() -> list[dict]:
    source = _kyocera_source()
    return [
        build_staged_record(
            brand="Kyocera",
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


def stage_kyocera_family_records() -> int:
    records = build_kyocera_family_records()
    errors = _validation_errors(records)
    if errors:
        raise ValueError("; ".join(errors))
    save_staged_records(
        "Kyocera",
        records,
        output_filename=OUTPUT_FILENAME,
    )
    return len(records)


def _kyocera_source() -> dict:
    matches = list_sources_by_brand("Kyocera")
    if not matches:
        raise ValueError("Kyocera source is not registered in catalog_sources.json.")
    return matches[0]


def _validation_errors(records: list[dict]) -> list[str]:
    errors: list[str] = []
    for index, record in enumerate(records):
        errors.extend(f"record {index}: {error}" for error in validate_staged_record(record))
    return errors


if __name__ == "__main__":
    count = stage_kyocera_family_records()
    print(f"Saved {count} staged Kyocera family records.")
