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


OUTPUT_FILENAME = "niagara_cutter_milling_families.json"
REVIEW_NOTE = "Family-level staged data needs human catalog review before production use."

FAMILY_SPECS = [
    {
        "tool_category": "endmill",
        "family_name": "Production square end mill families",
        "operation_fit": ["general_milling", "slotting", "profiling", "shoulder_milling"],
        "material_fit": ["P", "M", "K"],
        "strategy_fit": ["production_milling", "general_purpose", "job_shop_general"],
        "coating_or_grade": "verify coating family and flute style by catalog",
        "geometry_tags": ["square_end", "solid_carbide", "production_candidate"],
        "dimension_summary": "family-level production square end mill category only; verify flute count, reach, corner style, and material application by catalog",
    },
    {
        "tool_category": "endmill",
        "family_name": "Variable helix production end mill families",
        "operation_fit": ["general_milling", "profiling", "roughing", "finishing"],
        "material_fit": ["P", "M", "K", "S"],
        "strategy_fit": ["production_milling", "chatter_reduction_candidate", "high_performance"],
        "coating_or_grade": "verify coating family and helix style by catalog",
        "geometry_tags": ["variable_helix", "solid_carbide", "production_candidate"],
        "dimension_summary": "family-level variable helix production category only; verify flute count, reach, corner style, and target materials by catalog",
    },
    {
        "tool_category": "endmill",
        "family_name": "Roughing end mill families",
        "operation_fit": ["roughing", "slotting", "pocketing", "profiling"],
        "material_fit": ["P", "M", "K"],
        "strategy_fit": ["roughing", "material_removal_priority", "production_milling"],
        "coating_or_grade": "verify rougher form and coating family by catalog",
        "geometry_tags": ["roughing", "chipbreaker_candidate", "solid_carbide"],
        "dimension_summary": "family-level roughing end mill category only; verify serration style, flute count, reach, and application by catalog",
    },
    {
        "tool_category": "endmill",
        "family_name": "Corner radius production end mill families",
        "operation_fit": ["general_milling", "profiling", "roughing", "finishing"],
        "material_fit": ["P", "M", "K", "S"],
        "strategy_fit": ["edge_strength_priority", "production_milling", "high_performance"],
        "coating_or_grade": "verify corner radius family and coating by catalog",
        "geometry_tags": ["corner_radius", "solid_carbide", "production_candidate"],
        "dimension_summary": "family-level corner radius production category only; verify radius range, flute count, reach, and material application by catalog",
    },
    {
        "tool_category": "endmill",
        "family_name": "Finishing and contouring end mill families",
        "operation_fit": ["finishing", "profiling", "contouring", "wall_finishing"],
        "material_fit": ["P", "M", "K", "S", "H"],
        "strategy_fit": ["finishing", "surface_finish_priority", "production_milling"],
        "coating_or_grade": "verify finishing geometry and coating family by catalog",
        "geometry_tags": ["finishing", "contouring_candidate", "solid_carbide"],
        "dimension_summary": "family-level finishing and contouring category only; verify flute count, reach, corner style, and finish geometry by catalog",
    },
]


def build_niagara_cutter_family_records() -> list[dict]:
    source = _niagara_cutter_source()
    return [
        build_staged_record(
            brand="Niagara Cutter",
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


def stage_niagara_cutter_family_records() -> int:
    records = build_niagara_cutter_family_records()
    errors = _validation_errors(records)
    if errors:
        raise ValueError("; ".join(errors))
    save_staged_records(
        "Niagara Cutter",
        records,
        output_filename=OUTPUT_FILENAME,
    )
    return len(records)


def _niagara_cutter_source() -> dict:
    matches = list_sources_by_brand("Niagara Cutter")
    if not matches:
        raise ValueError("Niagara Cutter source is not registered in catalog_sources.json.")
    return matches[0]


def _validation_errors(records: list[dict]) -> list[str]:
    errors: list[str] = []
    for index, record in enumerate(records):
        errors.extend(f"record {index}: {error}" for error in validate_staged_record(record))
    return errors


if __name__ == "__main__":
    count = stage_niagara_cutter_family_records()
    print(f"Saved {count} staged Niagara Cutter family records.")
