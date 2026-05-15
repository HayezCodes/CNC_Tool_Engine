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


OUTPUT_FILENAME = "sumitomo_electric_insert_families.json"
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
        "family_name": "Heavy roughing turning insert families",
        "operation_fit": ["external_turning", "roughing", "shoulder_turning", "facing"],
        "material_fit": ["P", "M", "K", "S"],
        "strategy_fit": ["roughing", "production_turning", "edge_strength_priority"],
        "coating_or_grade": "verify roughing grade families and chipbreaker groups by catalog",
        "geometry_tags": ["turning_insert", "roughing", "grade_family_requires_review"],
        "dimension_summary": "family-level roughing turning insert category only; verify shape, chipbreaker family, grade family, and holder compatibility by catalog",
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
        "tool_category": "indexable_cutter",
        "family_name": "Indexable milling cutter system families",
        "operation_fit": ["face_milling", "shoulder_milling", "high_feed_milling", "copy_milling"],
        "material_fit": ["P", "M", "K", "N", "S", "H"],
        "strategy_fit": ["production_milling", "cutter_platform", "manual_catalog_review_required"],
        "coating_or_grade": "verify cutter platform and insert compatibility by catalog",
        "geometry_tags": ["indexable_cutter", "system_platform", "insert_compatibility_requires_review"],
        "dimension_summary": "family-level indexable cutter system category only; verify cutter platform, insert family, entering angle, and target operations by catalog",
    },
]


def build_sumitomo_electric_family_records() -> list[dict]:
    source = _sumitomo_electric_source()
    return [
        build_staged_record(
            brand="Sumitomo Electric",
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


def stage_sumitomo_electric_family_records() -> int:
    records = build_sumitomo_electric_family_records()
    errors = _validation_errors(records)
    if errors:
        raise ValueError("; ".join(errors))
    save_staged_records(
        "Sumitomo Electric",
        records,
        output_filename=OUTPUT_FILENAME,
    )
    return len(records)


def _sumitomo_electric_source() -> dict:
    matches = list_sources_by_brand("Sumitomo Electric")
    if not matches:
        raise ValueError("Sumitomo Electric source is not registered in catalog_sources.json.")
    return matches[0]


def _validation_errors(records: list[dict]) -> list[str]:
    errors: list[str] = []
    for index, record in enumerate(records):
        errors.extend(f"record {index}: {error}" for error in validate_staged_record(record))
    return errors


if __name__ == "__main__":
    count = stage_sumitomo_electric_family_records()
    print(f"Saved {count} staged Sumitomo Electric family records.")
