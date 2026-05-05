from app import build_turning_intent_profile


def _common(material_group: str, doc_band: str = "MEDIUM", finish_priority: str = "MEDIUM") -> dict[str, str]:
    return {
        "material_group": material_group,
        "doc_band": doc_band,
        "finish_priority": finish_priority,
    }


def test_p_steel_finishing_boosts_pf_and_mf_direction() -> None:
    profile = build_turning_intent_profile(_common("P", doc_band="LIGHT", finish_priority="HIGH"), "Finishing")
    assert profile["shop_preference"] == "PF"
    assert profile["chipbreaker_weights"]["PF"] > profile["chipbreaker_weights"]["MR"]
    assert "PF" in profile["primary_chipbreakers"]
    assert "MF" in profile["primary_chipbreakers"]


def test_p_steel_roughing_boosts_pr_mr_and_mrr_direction() -> None:
    profile = build_turning_intent_profile(_common("P", doc_band="HEAVY"), "Roughing")
    assert profile["shop_preference"] == "PR"
    assert profile["chipbreaker_weights"]["PR"] >= profile["chipbreaker_weights"]["MR"]
    assert "PR" in profile["primary_chipbreakers"]
    assert "MR" in profile["primary_chipbreakers"]
    assert "MRR" in profile["primary_chipbreakers"]


def test_medium_general_keeps_mf_and_mr_active() -> None:
    profile = build_turning_intent_profile(_common("P"), "Medium / General")
    assert profile["chipbreaker_weights"]["MF"] >= 2
    assert profile["chipbreaker_weights"]["MR"] >= 2
    assert "MF" in profile["primary_chipbreakers"]
    assert "MR" in profile["primary_chipbreakers"]


def test_non_p_material_does_not_apply_p_steel_shop_preference() -> None:
    profile = build_turning_intent_profile(_common("M", doc_band="LIGHT", finish_priority="HIGH"), "Finishing")
    assert profile["shop_preference"] is None
