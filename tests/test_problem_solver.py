import pytest

from grade_engine.problem_solver import solve_operation_problem


PROBLEM_TYPES = [
    "chatter",
    "poor_finish",
    "short_tool_life",
    "chip_control",
    "small_bore_access",
    "needs_value_option",
    "dynamic_milling",
    "specialty_feature",
    "production_turning",
]


@pytest.mark.parametrize("problem_type", PROBLEM_TYPES)
def test_each_problem_type_returns_recommendation(problem_type: str) -> None:
    result = solve_operation_problem(problem_type, "P", "general_milling", "balanced", "good")

    assert result["problem_type"] == problem_type
    assert result["recommended_direction"]
    assert result["brand_family_candidates"] or result["endmill_candidates"] or result["insert_candidates"]
    assert result["cautions"]
    assert result["verification_note"]


def test_small_bore_access_includes_micro_100() -> None:
    result = solve_operation_problem("small_bore_access", "P", "small_bore", "small_bore", "good")
    brands = {record["brand"] for record in result["brand_family_candidates"]}

    assert "Micro 100" in brands


def test_dynamic_milling_includes_helical_or_garr() -> None:
    result = solve_operation_problem("dynamic_milling", "P", "dynamic_milling", "high_performance", "good")
    brands = {record["brand"] for record in result["brand_family_candidates"]}
    endmill_brands = {record["brand"] for record in result["endmill_candidates"]}

    assert {"Helical Solutions", "Garr Tool"}.intersection(brands | endmill_brands)


def test_needs_value_option_includes_value_brands() -> None:
    result = solve_operation_problem("needs_value_option", "P", "general_milling", "value", "good")
    brands = {record["brand"] for record in result["brand_family_candidates"]}

    assert {"YG-1", "Accupro", "Hertel", "Haas Branded Tooling"}.intersection(brands)


def test_production_turning_includes_indexable_brands() -> None:
    result = solve_operation_problem("production_turning", "P", "production_turning", "production_turning", "good")
    brands = {record["brand"] for record in result["brand_family_candidates"]}
    insert_brands = {record["brand"] for record in result["insert_candidates"]}

    assert {"Sumitomo Electric", "Kyocera", "Tungaloy"}.issubset(brands | insert_brands)
