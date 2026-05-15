from grade_engine.brand_intelligence import infer_brand_intelligence_from_query


def _brands(records: list[dict]) -> set[str]:
    return {record["brand"] for record in records}


def test_harvey_chamfer_cutter_returns_specialty_direction() -> None:
    result = infer_brand_intelligence_from_query("Harvey chamfer cutter")

    assert "Harvey Tool" in result["brand_matches"]
    assert "chamfer" in result["operation_matches"]
    assert "Harvey Tool" in _brands(result["recommended_brands"]) | _brands(result["endmill_candidates"])


def test_micro_100_boring_bar_returns_small_bore_direction() -> None:
    result = infer_brand_intelligence_from_query("Micro 100 boring bar")

    assert "Micro 100" in result["brand_matches"]
    assert "small_bore" in result["operation_matches"]
    assert "Micro 100" in _brands(result["recommended_brands"])


def test_helical_dynamic_endmill_returns_dynamic_direction() -> None:
    result = infer_brand_intelligence_from_query("Helical dynamic endmill")

    assert "Helical Solutions" in result["brand_matches"]
    assert "dynamic_milling" in result["operation_matches"]
    assert "Helical Solutions" in _brands(result["recommended_brands"]) | _brands(result["endmill_candidates"])


def test_sumitomo_turning_insert_returns_insert_candidates() -> None:
    result = infer_brand_intelligence_from_query("Sumitomo turning insert")

    assert "Sumitomo Electric" in result["brand_matches"]
    assert "turning" in result["operation_matches"]
    assert "Sumitomo Electric" in _brands(result["recommended_brands"]) | _brands(result["insert_candidates"])
    assert result["insert_candidates"]


def test_unknown_query_returns_safe_empty_structure() -> None:
    result = infer_brand_intelligence_from_query("left handed sky hook")

    assert result["matched_terms"] == []
    assert result["brand_matches"] == []
    assert result["operation_matches"] == []
    assert result["recommended_brands"] == []
    assert result["endmill_candidates"] == []
    assert result["insert_candidates"] == []
    assert result["notes"]
    assert result["verification_note"]
