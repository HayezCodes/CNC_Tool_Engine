from grade_engine.brand_intelligence import (
    recommend_brand_families,
    recommend_endmill_families,
    recommend_insert_grade_families,
)
from grade_engine.problem_solver import solve_operation_problem
from grade_engine.reviewed_catalog_boosting import (
    calculate_reviewed_family_boost,
    load_reviewed_family_boost_data,
    merge_reviewed_boosts_into_recommendations,
)


FORBIDDEN_TERMS = {"sfm", "rpm", "feed", "feeds", "speeds", "diameter", "dimensions", "catalog_number"}


def test_reviewed_boost_data_loads() -> None:
    records = load_reviewed_family_boost_data()

    assert records
    assert all(record["brand"] for record in records)
    assert all(record["family_name"] for record in records)
    assert all(isinstance(record["family_type"], set) for record in records)


def test_helical_boosts_dynamic_milling() -> None:
    boosts = calculate_reviewed_family_boost("dynamic_milling", "P", strategy="dynamic")

    top_brands = [item["brand"] for item in boosts["brand_boosts"][:3]]
    assert "Helical Solutions" in top_brands
    helical = next(item for item in boosts["brand_boosts"] if item["brand"] == "Helical Solutions")
    assert any("dynamic/adaptive milling family match" in reason for reason in helical["matched_reasons"])
    assert boosts["verification_note"]


def test_harvey_boosts_chamfer_and_specialty() -> None:
    boosts = calculate_reviewed_family_boost("chamfer", "P", strategy="specialty")
    brands = [item["brand"] for item in boosts["brand_boosts"][:3]]

    assert "Harvey Tool" in brands
    harvey = next(item for item in boosts["brand_boosts"] if item["brand"] == "Harvey Tool")
    assert any("chamfer" in reason or "specialty" in reason for reason in harvey["matched_reasons"])


def test_micro_100_boosts_small_bore() -> None:
    boosts = calculate_reviewed_family_boost("small_bore", "P", strategy="small_bore", problem_type="small_bore_access")

    top_brands = [item["brand"] for item in boosts["brand_boosts"][:3]]
    assert "Micro 100" in top_brands


def test_sumitomo_kyocera_tungaloy_boost_production_turning() -> None:
    boosts = calculate_reviewed_family_boost("production_turning", "P", strategy="production_turning")
    brands = {item["brand"] for item in boosts["brand_boosts"][:5]}

    assert {"Sumitomo Electric", "Kyocera", "Tungaloy"}.issubset(brands)


def test_merge_preserves_original_recommendations() -> None:
    base = [
        {"brand": "Helical Solutions", "score": 10, "reasons": ["base reason"]},
        {"brand": "Accupro", "score": 8, "reasons": ["base value reason"]},
    ]
    boosts = calculate_reviewed_family_boost("dynamic_milling", "P", strategy="dynamic")

    merged = merge_reviewed_boosts_into_recommendations(base, boosts)

    assert len(merged) == len(base)
    assert {item["brand"] for item in merged} == {"Helical Solutions", "Accupro"}
    assert all(item.get("reviewed_catalog_verification_note") for item in merged)


def test_merge_only_boosts_confidence_modestly() -> None:
    base = [
        {"brand": "Helical Solutions", "score": 10, "reasons": ["base reason"]},
        {"brand": "Harvey Tool", "score": 9, "reasons": ["base reason"]},
    ]
    boosts = calculate_reviewed_family_boost("dynamic_milling", "P", strategy="dynamic")

    merged = merge_reviewed_boosts_into_recommendations(base, boosts)
    score_map = {item["brand"]: item["score"] for item in merged}

    assert 10 <= score_map["Helical Solutions"] <= 13
    assert 9 <= score_map["Harvey Tool"] <= 12
    helical = next(item for item in merged if item["brand"] == "Helical Solutions")
    assert helical["reviewed_catalog_support"]["ranking_adjustment"] <= 3


def test_boost_outputs_do_not_include_speeds_feeds_or_dimensions() -> None:
    outputs = [
        calculate_reviewed_family_boost("dynamic_milling", "P", strategy="dynamic"),
        calculate_reviewed_family_boost("chamfer", "P", strategy="specialty"),
        calculate_reviewed_family_boost("production_turning", "P", strategy="production_turning"),
    ]
    text = " ".join(str(item).lower() for item in outputs)

    for forbidden in FORBIDDEN_TERMS:
        assert forbidden not in text


def test_all_boost_outputs_include_verification_note() -> None:
    boosts = calculate_reviewed_family_boost("general_milling", "P", strategy="balanced")

    assert boosts["verification_note"]


def test_recommendations_expose_reviewed_support_without_replacing_base_logic() -> None:
    brand_recommendations = recommend_brand_families("small_bore", "P", "small_bore")
    endmill_recommendations = recommend_endmill_families("chamfer", "P", strategy="specialty", priority="specialty")
    insert_recommendations = recommend_insert_grade_families("production_turning", "P", "production_turning")

    assert any(item["brand"] == "Micro 100" and item.get("reviewed_catalog_support") for item in brand_recommendations)
    assert any(item["brand"] == "Harvey Tool" and item.get("reviewed_catalog_support") for item in endmill_recommendations)
    assert any(item["brand"] in {"Sumitomo Electric", "Kyocera", "Tungaloy"} and item.get("reviewed_catalog_support") for item in insert_recommendations)


def test_problem_solver_includes_reviewed_support_summary() -> None:
    result = solve_operation_problem("production_turning", "P", "production_turning", "production_turning", "good")

    assert result["reviewed_catalog_support"]["verification_note"]
    brands = {item["brand"] for item in result["reviewed_catalog_support"]["brand_boosts"][:5]}
    assert {"Sumitomo Electric", "Kyocera", "Tungaloy"}.intersection(brands)
