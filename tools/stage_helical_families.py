import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.catalog_ingestion import (
    build_staged_record,
    list_sources_by_brand,
    save_staged_records,
    validate_staged_record,
)


OUTPUT_FILENAME = "helical_solutions_endmill_families.json"
REVIEW_NOTE = "Family-level staged data needs human catalog review before production use."

FAMILY_SPECS = [
    {
        "tool_category": "endmill",
        "family_name": "High-performance square end mill families",
        "operation_fit": ["general_milling", "slotting", "profiling", "roughing", "finishing"],
        "material_fit": ["P", "M", "K", "N", "S", "H"],
        "strategy_fit": ["high_performance", "job_shop_general", "production_milling"],
        "coating_or_grade": "verify coating family by catalog",
        "geometry_tags": ["square_end", "solid_carbide", "high_performance"],
        "dimension_summary": "family-level square end mill category only; verify size, reach, flute count, and corner details by catalog",
    },
    {
        "tool_category": "endmill",
        "family_name": "Variable pitch end mill families",
        "operation_fit": ["general_milling", "profiling", "roughing", "finishing"],
        "material_fit": ["P", "M", "K", "S", "H"],
        "strategy_fit": ["high_performance", "chatter_reduction_candidate", "production_milling"],
        "coating_or_grade": "verify coating family by catalog",
        "geometry_tags": ["variable_pitch", "solid_carbide", "chatter_reduction_candidate"],
        "dimension_summary": "family-level variable pitch category only; verify size, reach, flute count, helix, and corner details by catalog",
    },
    {
        "tool_category": "endmill",
        "family_name": "Dynamic/adaptive milling end mill families",
        "operation_fit": ["dynamic_milling", "adaptive_milling", "roughing", "profiling"],
        "material_fit": ["P", "M", "K", "S", "H"],
        "strategy_fit": ["dynamic", "adaptive", "high_efficiency", "radial_engagement_strategy"],
        "coating_or_grade": "verify coating family by catalog or manufacturer advisor",
        "geometry_tags": ["dynamic_milling", "adaptive_milling", "solid_carbide", "chip_evacuation_candidate"],
        "dimension_summary": "family-level dynamic milling category only; verify size, reach, flute count, chip clearance, and toolpath limits by catalog",
    },
    {
        "tool_category": "endmill",
        "family_name": "Aluminum end mill families",
        "operation_fit": ["aluminum_milling", "slotting", "profiling", "roughing", "finishing"],
        "material_fit": ["N"],
        "strategy_fit": ["aluminum_milling", "high_efficiency", "chip_evacuation_priority"],
        "coating_or_grade": "verify polished, coated, or uncoated configuration by catalog",
        "geometry_tags": ["aluminum_geometry", "high_rake_candidate", "chip_evacuation_candidate"],
        "dimension_summary": "family-level aluminum milling category only; verify size, reach, flute count, coating, and chip clearance by catalog",
    },
    {
        "tool_category": "endmill",
        "family_name": "Finishing end mill families",
        "operation_fit": ["finishing", "profiling", "wall_finishing", "floor_finishing"],
        "material_fit": ["P", "M", "K", "N", "S", "H"],
        "strategy_fit": ["finishing", "surface_finish_priority", "light_radial_engagement"],
        "coating_or_grade": "verify coating family by catalog",
        "geometry_tags": ["finishing", "solid_carbide", "surface_finish_candidate"],
        "dimension_summary": "family-level finishing category only; verify size, reach, flute count, corner style, and finish geometry by catalog",
    },
    {
        "tool_category": "endmill",
        "family_name": "Roughing end mill families",
        "operation_fit": ["roughing", "slotting", "pocketing", "profiling"],
        "material_fit": ["P", "M", "K", "S", "H"],
        "strategy_fit": ["roughing", "high_performance", "production_milling"],
        "coating_or_grade": "verify coating family by catalog",
        "geometry_tags": ["roughing", "chipbreaker_candidate", "solid_carbide"],
        "dimension_summary": "family-level roughing category only; verify size, reach, flute count, chipbreaker style, and corner details by catalog",
    },
    {
        "tool_category": "endmill",
        "family_name": "Corner radius end mill families",
        "operation_fit": ["general_milling", "profiling", "roughing", "finishing"],
        "material_fit": ["P", "M", "K", "N", "S", "H"],
        "strategy_fit": ["edge_strength_priority", "high_performance", "job_shop_general"],
        "coating_or_grade": "verify coating family by catalog",
        "geometry_tags": ["corner_radius", "solid_carbide", "edge_strength_candidate"],
        "dimension_summary": "family-level corner radius category only; verify size, reach, flute count, radius, and material application by catalog",
    },
    {
        "tool_category": "endmill",
        "family_name": "Ball end mill families",
        "operation_fit": ["contouring", "finishing", "3d_milling", "profiling"],
        "material_fit": ["P", "M", "K", "N", "S", "H"],
        "strategy_fit": ["3d_finishing", "surface_finish_priority", "contouring"],
        "coating_or_grade": "verify coating family by catalog",
        "geometry_tags": ["ball_end", "solid_carbide", "contouring_candidate"],
        "dimension_summary": "family-level ball end mill category only; verify size, reach, flute count, and neck clearance by catalog",
    },
    {
        "tool_category": "chamfer_mill",
        "family_name": "Chamfer mill families",
        "operation_fit": ["chamfer", "deburring", "edge_breaking", "spotting"],
        "material_fit": ["P", "M", "K", "N", "S", "H"],
        "strategy_fit": ["chamfering", "edge_breaking", "specialty_milling"],
        "coating_or_grade": "verify coating family by catalog",
        "geometry_tags": ["chamfer_mill", "angle_geometry_requires_review", "solid_carbide"],
        "dimension_summary": "family-level chamfer mill category only; verify included angle, size, flute count, and reach by catalog",
    },
    {
        "tool_category": "specialty_milling",
        "family_name": "Specialty milling cutter families",
        "operation_fit": ["specialty_milling", "undercutting", "profiling", "feature_milling"],
        "material_fit": ["P", "M", "K", "N", "S", "H"],
        "strategy_fit": ["specialty_feature", "problem_solving", "manual_catalog_review_required"],
        "coating_or_grade": "verify coating family by catalog",
        "geometry_tags": ["specialty_milling", "geometry_requires_review", "solid_carbide"],
        "dimension_summary": "family-level specialty milling category only; verify exact cutter form, clearance, reach, and application by catalog",
    },
]


def build_helical_family_records() -> list[dict]:
    source = _helical_source()
    return [
        build_staged_record(
            brand="Helical Solutions",
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


def stage_helical_family_records() -> int:
    records = build_helical_family_records()
    errors = _validation_errors(records)
    if errors:
        raise ValueError("; ".join(errors))
    save_staged_records(
        "Helical Solutions",
        records,
        output_filename=OUTPUT_FILENAME,
    )
    return len(records)


def _helical_source() -> dict:
    matches = list_sources_by_brand("Helical Solutions")
    if not matches:
        raise ValueError("Helical Solutions source is not registered in catalog_sources.json.")
    return matches[0]


def _validation_errors(records: list[dict]) -> list[str]:
    errors: list[str] = []
    for index, record in enumerate(records):
        errors.extend(f"record {index}: {error}" for error in validate_staged_record(record))
    return errors


if __name__ == "__main__":
    count = stage_helical_family_records()
    print(f"Saved {count} staged Helical Solutions endmill family records.")
