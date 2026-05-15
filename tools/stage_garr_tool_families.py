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


OUTPUT_FILENAME = "garr_tool_endmill_families.json"
REVIEW_NOTE = "Family-level staged data needs human catalog review before production use."

FAMILY_SPECS = [
    {
        "tool_category": "endmill",
        "family_name": "High-performance square end mill families",
        "operation_fit": ["general_milling", "slotting", "profiling", "roughing"],
        "material_fit": ["P", "M", "K", "S", "H"],
        "strategy_fit": ["high_performance", "production_milling", "material_removal_priority"],
        "coating_or_grade": "verify coating family and flute style by catalog",
        "geometry_tags": ["square_end", "solid_carbide", "high_performance"],
        "dimension_summary": "family-level high-performance square end mill category only; verify flute count, reach, and corner style by catalog",
    },
    {
        "tool_category": "endmill",
        "family_name": "High-efficiency roughing end mill families",
        "operation_fit": ["roughing", "dynamic_milling", "pocketing", "profiling"],
        "material_fit": ["P", "M", "K", "S"],
        "strategy_fit": ["high_efficiency", "roughing", "radial_engagement_strategy"],
        "coating_or_grade": "verify roughing geometry and coating family by catalog",
        "geometry_tags": ["roughing", "high_efficiency", "solid_carbide"],
        "dimension_summary": "family-level roughing end mill category only; verify flute count, chipbreaker style, reach, and material application by catalog",
    },
    {
        "tool_category": "endmill",
        "family_name": "Variable helix finishing end mill families",
        "operation_fit": ["finishing", "profiling", "wall_finishing", "floor_finishing"],
        "material_fit": ["P", "M", "K", "S", "H"],
        "strategy_fit": ["finishing", "surface_finish_priority", "chatter_reduction_candidate"],
        "coating_or_grade": "verify finishing geometry and coating family by catalog",
        "geometry_tags": ["variable_helix", "finishing", "solid_carbide"],
        "dimension_summary": "family-level finishing end mill category only; verify flute count, reach, corner style, and finish geometry by catalog",
    },
    {
        "tool_category": "endmill",
        "family_name": "Corner radius end mill families",
        "operation_fit": ["general_milling", "profiling", "roughing", "finishing"],
        "material_fit": ["P", "M", "K", "S", "H"],
        "strategy_fit": ["edge_strength_priority", "high_performance", "production_milling"],
        "coating_or_grade": "verify corner radius family and coating by catalog",
        "geometry_tags": ["corner_radius", "solid_carbide", "edge_strength_candidate"],
        "dimension_summary": "family-level corner radius end mill category only; verify radius range, flute count, reach, and application by catalog",
    },
    {
        "tool_category": "endmill",
        "family_name": "Aerospace and hard-metal finishing end mill families",
        "operation_fit": ["finishing", "profiling", "contouring", "shoulder_milling"],
        "material_fit": ["M", "S", "H"],
        "strategy_fit": ["finishing", "difficult_material_focus", "high_performance"],
        "coating_or_grade": "verify coating family and substrate by catalog",
        "geometry_tags": ["finishing", "difficult_material_candidate", "solid_carbide"],
        "dimension_summary": "family-level difficult-material finishing category only; verify flute count, reach, corner style, and target materials by catalog",
    },
    {
        "tool_category": "endmill",
        "family_name": "Aluminum milling end mill families",
        "operation_fit": ["aluminum_milling", "slotting", "profiling", "finishing"],
        "material_fit": ["N"],
        "strategy_fit": ["high_efficiency", "surface_finish_priority", "chip_evacuation_priority"],
        "coating_or_grade": "verify aluminum-focused substrate and coating family by catalog",
        "geometry_tags": ["aluminum_geometry", "high_rake_candidate", "solid_carbide"],
        "dimension_summary": "family-level aluminum milling category only; verify flute count, polish/coating style, reach, and chip evacuation geometry by catalog",
    },
]


def build_garr_tool_family_records() -> list[dict]:
    source = _garr_tool_source()
    return [
        build_staged_record(
            brand="Garr Tool",
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


def stage_garr_tool_family_records() -> int:
    records = build_garr_tool_family_records()
    errors = _validation_errors(records)
    if errors:
        raise ValueError("; ".join(errors))
    save_staged_records(
        "Garr Tool",
        records,
        output_filename=OUTPUT_FILENAME,
    )
    return len(records)


def _garr_tool_source() -> dict:
    matches = list_sources_by_brand("Garr Tool")
    if not matches:
        raise ValueError("Garr Tool source is not registered in catalog_sources.json.")
    return matches[0]


def _validation_errors(records: list[dict]) -> list[str]:
    errors: list[str] = []
    for index, record in enumerate(records):
        errors.extend(f"record {index}: {error}" for error in validate_staged_record(record))
    return errors


if __name__ == "__main__":
    count = stage_garr_tool_family_records()
    print(f"Saved {count} staged Garr Tool family records.")
