from typing import Any

from grade_engine.brand_intelligence import (
    recommend_brand_families,
    recommend_endmill_families,
    recommend_insert_grade_families,
)


PROBLEM_DIRECTIONS = {
    "chatter": "Favor more stable geometry, shorter projection, stronger setup, and families known for production stability or high-performance milling.",
    "poor_finish": "Favor finishing-oriented geometry, stable holders, proper chip control, and families with finishing candidate behavior.",
    "short_tool_life": "Favor wear-resistance or production-stability candidates, then verify grade/coating and heat management in the catalog.",
    "chip_control": "Favor chipbreaker-focused insert families or endmill families with chip evacuation support.",
    "small_bore_access": "Favor miniature boring and small-ID capable tooling families, then verify minimum bore access and projection.",
    "needs_value_option": "Favor practical value families while checking that the geometry is not a false economy for the material and setup.",
    "dynamic_milling": "Favor high-performance endmill families suited to adaptive or dynamic milling strategies.",
    "specialty_feature": "Favor specialty and miniature cutter families for features a standard endmill family will not solve cleanly.",
    "production_turning": "Favor production insert families and verify the exact grade/chipbreaker/application range before release.",
}

PROBLEM_PRIORITY = {
    "small_bore_access": "small_bore",
    "needs_value_option": "value",
    "dynamic_milling": "high_performance",
    "specialty_feature": "specialty",
    "production_turning": "production_turning",
    "chatter": "high_performance",
    "poor_finish": "balanced",
    "short_tool_life": "production_turning",
    "chip_control": "production_turning",
}

ENDMILL_PROBLEMS = {"chatter", "poor_finish", "short_tool_life", "chip_control", "dynamic_milling", "specialty_feature", "needs_value_option"}
INSERT_PROBLEMS = {"chatter", "poor_finish", "short_tool_life", "chip_control", "production_turning"}


def solve_operation_problem(
    problem_type: str,
    material_group: str,
    operation: str,
    priority: str = "balanced",
    setup_rigidity: str = "good",
) -> dict[str, Any]:
    problem_key = _normalize(problem_type)
    operation_key = _normalize(operation)
    priority_key = _normalize(priority)
    effective_priority = PROBLEM_PRIORITY.get(problem_key, priority_key)
    direction = PROBLEM_DIRECTIONS.get(
        problem_key,
        "Use family-level brand guidance as a starting point, then verify the exact tool in the manufacturer catalog.",
    )

    brand_candidates = recommend_brand_families(operation_key, material_group, effective_priority)[:5]
    endmill_candidates: list[dict[str, Any]] = []
    insert_candidates: list[dict[str, Any]] = []

    if problem_key == "small_bore_access":
        brand_candidates = recommend_brand_families("small_bore", material_group, "small_bore")[:5]
    elif problem_key == "needs_value_option":
        brand_candidates = recommend_brand_families(operation_key, material_group, "value")[:6]
    elif problem_key == "dynamic_milling":
        brand_candidates = recommend_brand_families("dynamic_milling", material_group, "high_performance")[:5]

    if problem_key in ENDMILL_PROBLEMS or operation_key in {"general_milling", "dynamic_milling", "aluminum_milling", "chamfer", "keyseat", "specialty"}:
        endmill_operation = _problem_endmill_operation(problem_key, operation_key)
        endmill_strategy = "dynamic" if problem_key == "dynamic_milling" else priority_key
        endmill_candidates = recommend_endmill_families(
            endmill_operation,
            material_group,
            strategy=endmill_strategy,
            priority=effective_priority,
        )[:5]

    if problem_key in INSERT_PROBLEMS or operation_key in {"turning", "production_turning", "grooving", "threading"}:
        insert_operation = "production_turning" if problem_key == "production_turning" else operation_key
        insert_candidates = recommend_insert_grade_families(insert_operation, material_group, effective_priority)[:5]

    cautions = _build_cautions(problem_key, setup_rigidity)
    return {
        "problem_type": problem_key,
        "recommended_direction": direction,
        "brand_family_candidates": brand_candidates,
        "endmill_candidates": endmill_candidates,
        "insert_candidates": insert_candidates,
        "cautions": cautions,
        "verification_note": "Family-level guidance only. Verify exact tool selection, geometry, dimensions, grade, chipbreaker, holder compatibility, and cutting data with the manufacturer catalog.",
    }


def _problem_endmill_operation(problem_type: str, operation: str) -> str:
    if problem_type == "dynamic_milling":
        return "dynamic_milling"
    if problem_type == "specialty_feature":
        return "specialty"
    if operation in {"chamfer", "keyseat", "specialty", "small_bore"}:
        return operation
    return "general_milling"


def _build_cautions(problem_type: str, setup_rigidity: str) -> list[str]:
    cautions = [
        "Do not treat family-level guidance as certified speeds, feeds, dimensions, or catalog-number selection.",
        "Confirm coating, geometry, holder fit, reach/projection, coolant access, and material application range before release.",
    ]
    if _normalize(setup_rigidity) in {"poor", "low", "light", "weak"}:
        cautions.append("Low setup rigidity may require reducing projection, improving workholding, or selecting a tougher geometry.")
    if problem_type == "small_bore_access":
        cautions.append("Verify minimum bore access, neck clearance, projection, deflection risk, and tool geometry before ordering.")
    if problem_type == "dynamic_milling":
        cautions.append("Verify flute count, coating, chip evacuation, radial engagement, CAM strategy, and machine limits.")
    if problem_type == "needs_value_option":
        cautions.append("Avoid false economy in hard materials, long reach, interrupted cuts, or unattended production work.")
    if problem_type == "production_turning":
        cautions.append("Verify grade, chipbreaker, insert shape, edge prep, and holder clamping for the exact operation.")
    return cautions


def _normalize(value: object) -> str:
    return str(value).strip().lower().replace(" ", "_").replace("-", "_")
