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


OUTPUT_FILENAME = "yg_1_general_cutting_families.json"
REVIEW_NOTE = "Family-level staged data needs human catalog review before production use."

FAMILY_SPECS = [
    {
        "tool_category": "endmill",
        "family_name": "General-purpose carbide end mill families",
        "operation_fit": ["general_milling", "slotting", "profiling", "shoulder_milling"],
        "material_fit": ["P", "M", "K", "N"],
        "strategy_fit": ["job_shop_general", "value_focused", "general_purpose"],
        "coating_or_grade": "verify coating family and flute style by catalog",
        "geometry_tags": ["solid_carbide", "general_purpose", "square_end_candidate"],
        "dimension_summary": "family-level general carbide end mill category only; verify flute count, reach, corner style, and material application by catalog",
    },
    {
        "tool_category": "endmill",
        "family_name": "Variable helix performance end mill families",
        "operation_fit": ["general_milling", "profiling", "roughing", "finishing"],
        "material_fit": ["P", "M", "K", "S"],
        "strategy_fit": ["chatter_reduction_candidate", "high_performance", "production_milling"],
        "coating_or_grade": "verify coating family and helix style by catalog",
        "geometry_tags": ["variable_helix", "solid_carbide", "chatter_reduction_candidate"],
        "dimension_summary": "family-level variable helix end mill category only; verify flute count, reach, corner style, and application limits by catalog",
    },
    {
        "tool_category": "endmill",
        "family_name": "Roughing end mill families",
        "operation_fit": ["roughing", "slotting", "pocketing", "profiling"],
        "material_fit": ["P", "M", "K"],
        "strategy_fit": ["roughing", "production_milling", "material_removal_priority"],
        "coating_or_grade": "verify rougher form and coating family by catalog",
        "geometry_tags": ["roughing", "chipbreaker_candidate", "solid_carbide"],
        "dimension_summary": "family-level roughing end mill category only; verify serration style, flute count, reach, and material application by catalog",
    },
    {
        "tool_category": "drill",
        "family_name": "General-purpose carbide drill families",
        "operation_fit": ["drilling", "through_hole_drilling", "blind_hole_drilling"],
        "material_fit": ["P", "M", "K", "N"],
        "strategy_fit": ["general_purpose", "job_shop_general", "value_focused"],
        "coating_or_grade": "verify drill substrate and coating family by catalog",
        "geometry_tags": ["solid_drill", "general_purpose", "through_coolant_requires_review"],
        "dimension_summary": "family-level carbide drill category only; verify point style, coolant style, diameter range, and depth series by catalog",
    },
    {
        "tool_category": "drill",
        "family_name": "Performance drill families",
        "operation_fit": ["drilling", "through_hole_drilling", "high_efficiency_drilling"],
        "material_fit": ["P", "M", "K", "S"],
        "strategy_fit": ["production_drilling", "through_coolant_candidate", "high_performance"],
        "coating_or_grade": "verify performance drill substrate and coating family by catalog",
        "geometry_tags": ["solid_drill", "high_performance", "through_coolant_requires_review"],
        "dimension_summary": "family-level performance drill category only; verify coolant style, point geometry, diameter range, and depth series by catalog",
    },
    {
        "tool_category": "tap",
        "family_name": "Machine tap families",
        "operation_fit": ["threading", "tapping", "internal_threading"],
        "material_fit": ["P", "M", "K", "N", "S"],
        "strategy_fit": ["machine_tapping", "production_threading", "manual_catalog_review_required"],
        "coating_or_grade": "verify substrate, coating family, and thread form by catalog",
        "geometry_tags": ["tap", "thread_form_requires_review", "spiral_point_or_spiral_flute_requires_review"],
        "dimension_summary": "family-level machine tap category only; verify thread form, pitch range, chamfer style, coolant style, and material application by catalog",
    },
]


def build_yg_1_family_records() -> list[dict]:
    source = _yg_1_source()
    return [
        build_staged_record(
            brand="YG-1",
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


def stage_yg_1_family_records() -> int:
    records = build_yg_1_family_records()
    errors = _validation_errors(records)
    if errors:
        raise ValueError("; ".join(errors))
    save_staged_records(
        "YG-1",
        records,
        output_filename=OUTPUT_FILENAME,
    )
    return len(records)


def _yg_1_source() -> dict:
    matches = list_sources_by_brand("YG-1")
    if not matches:
        raise ValueError("YG-1 source is not registered in catalog_sources.json.")
    return matches[0]


def _validation_errors(records: list[dict]) -> list[str]:
    errors: list[str] = []
    for index, record in enumerate(records):
        errors.extend(f"record {index}: {error}" for error in validate_staged_record(record))
    return errors


if __name__ == "__main__":
    count = stage_yg_1_family_records()
    print(f"Saved {count} staged YG-1 family records.")
