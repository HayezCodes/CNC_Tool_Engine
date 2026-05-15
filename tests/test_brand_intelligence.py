from grade_engine.brand_intelligence import (
    filter_brands_by_operation,
    get_brand_names,
    load_brand_intelligence,
    load_endmill_families,
    load_insert_grade_families,
    recommend_brand_families,
    recommend_endmill_families,
    recommend_insert_grade_families,
)


EXPECTED_BRANDS = {
    "YG-1",
    "Helical Solutions",
    "Niagara Cutter",
    "Harvey Tool",
    "Micro 100",
    "Garr Tool",
    "Sumitomo Electric",
    "Kyocera",
    "Tungaloy",
    "Accupro",
    "Hertel",
    "Haas Branded Tooling",
}

REQUIRED_KEYS = {
    "brand",
    "brand_type",
    "primary_strengths",
    "best_fit_operations",
    "material_strengths",
    "shop_use_notes",
    "recommended_engine_use",
    "source_status",
    "source_notes",
    "official_source_label",
    "official_source_url",
    "source_type",
    "last_reviewed",
    "verification_level",
}

ENDMILL_REQUIRED_KEYS = {
    "brand",
    "family_name",
    "family_type",
    "operation_fit",
    "material_fit",
    "strategy_fit",
    "strengths",
    "cautions",
    "source_status",
    "verification_level",
}

INSERT_REQUIRED_KEYS = {
    "brand",
    "insert_focus",
    "material_fit",
    "application_fit",
    "grade_behavior_tags",
    "chipbreaker_behavior_tags",
    "shop_use_notes",
    "source_status",
    "verification_level",
}

FORBIDDEN_EXACT_CLAIMS = {
    "catalog_number",
    "manufacturer_number",
    "sfm",
    "rpm",
    "feed per tooth",
    "chip load",
    "diameter_range",
    "exact dimension",
    "certified cutting data",
}


def test_brand_intelligence_json_loads() -> None:
    records = load_brand_intelligence()

    assert records
    assert isinstance(records, list)


def test_all_required_brand_names_exist() -> None:
    assert EXPECTED_BRANDS.issubset(set(get_brand_names()))


def test_required_keys_exist_on_every_brand_record() -> None:
    for record in load_brand_intelligence():
        assert REQUIRED_KEYS.issubset(record.keys())
        assert record["source_status"] == "family_level_verified_brand_scope_not_catalog_dimensions"


def test_specialty_filters_return_harvey_tool() -> None:
    for operation in ["specialty", "chamfer", "keyseat"]:
        brands = {record["brand"] for record in filter_brands_by_operation(operation)}
        assert "Harvey Tool" in brands


def test_small_bore_priority_returns_micro_100_near_top() -> None:
    recommendations = recommend_brand_families("small_bore", "P", "small_bore")
    brands = [record["brand"] for record in recommendations[:3]]

    assert "Micro 100" in brands


def test_value_priority_returns_value_candidates() -> None:
    recommendations = recommend_brand_families("general_milling", "P", "value")
    brands = {record["brand"] for record in recommendations}

    assert {"YG-1", "Accupro", "Hertel", "Haas Branded Tooling"}.issubset(brands)


def test_production_turning_priority_returns_indexable_candidates() -> None:
    recommendations = recommend_brand_families("production_turning", "P", "production_turning")
    brands = {record["brand"] for record in recommendations[:5]}

    assert {"Sumitomo Electric", "Kyocera", "Tungaloy"}.issubset(brands)


def test_no_recommendation_claims_exact_dimensions_or_feeds_speeds() -> None:
    records = [
        *load_brand_intelligence(),
        *load_endmill_families(),
        *load_insert_grade_families(),
    ]
    combined_text = " ".join(str(record).lower() for record in records)

    for forbidden in FORBIDDEN_EXACT_CLAIMS:
        assert forbidden not in combined_text


def test_endmill_families_load_and_have_required_keys() -> None:
    records = load_endmill_families()

    assert records
    for record in records:
        assert ENDMILL_REQUIRED_KEYS.issubset(record.keys())


def test_helical_ranks_well_for_dynamic_milling() -> None:
    recommendations = recommend_endmill_families("dynamic_milling", "P", strategy="dynamic", priority="high_performance")
    brands = [record["brand"] for record in recommendations[:3]]

    assert "Helical Solutions" in brands


def test_harvey_ranks_well_for_specialty_small_chamfer_keyseat() -> None:
    for operation in ["specialty", "small_bore", "chamfer", "keyseat"]:
        recommendations = recommend_endmill_families(operation, "P", strategy="specialty", priority="specialty")
        assert recommendations[0]["brand"] == "Harvey Tool"


def test_value_endmill_candidates_are_returned() -> None:
    recommendations = recommend_endmill_families("general_milling", "P", strategy="value", priority="value")
    brands = {record["brand"] for record in recommendations}

    assert {"YG-1", "Accupro", "Hertel", "Haas Branded Tooling"}.issubset(brands)


def test_insert_grade_families_load_and_have_required_keys() -> None:
    records = load_insert_grade_families()

    assert records
    for record in records:
        assert INSERT_REQUIRED_KEYS.issubset(record.keys())


def test_production_turning_favors_insert_candidates() -> None:
    recommendations = recommend_insert_grade_families("production_turning", "P", "production_turning")
    brands = {record["brand"] for record in recommendations[:4]}

    assert {"Sumitomo Electric", "Kyocera", "Tungaloy"}.issubset(brands)


def test_interrupted_roughing_returns_toughness_candidates() -> None:
    recommendations = recommend_insert_grade_families("interrupted_cut_candidate", "P", "production_turning")

    assert recommendations
    assert any("toughness_candidate" in record["grade_behavior_tags"] for record in recommendations)


def test_insert_family_data_has_no_false_exact_equivalent_claims() -> None:
    combined_text = " ".join(str(record).lower() for record in load_insert_grade_families())

    assert "equivalent grade" not in combined_text
    assert "exact equivalent" not in combined_text
