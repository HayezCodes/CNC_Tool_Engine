import pytest

from grade_engine.engine import resolve_grade_behavior
from grade_engine.enums import APPLICATION_ZONES, MATERIAL_GROUPS


EXPECTED_KEYS = {
    "material_group",
    "application_zone",
    "required_toughness",
    "required_wear_resistance",
    "preferred_coating",
    "insert_identity",
    "risk_flags",
    "recommendation_title",
}


def make_input(material_group: str, application_zone: str) -> dict[str, str]:
    return {
        "material_group": material_group,
        "application_zone": application_zone,
        "interrupted_cut": "NONE",
        "stickout": "NORMAL",
        "workholding": "GOOD",
        "cutting_speed_band": "NORMAL",
        "doc_band": "MEDIUM",
        "finish_priority": "NORMAL",
    }


@pytest.mark.parametrize("material_group", MATERIAL_GROUPS)
@pytest.mark.parametrize("application_zone", APPLICATION_ZONES)
def test_resolve_grade_behavior_smoke(material_group: str, application_zone: str) -> None:
    result = resolve_grade_behavior(make_input(material_group, application_zone))

    assert EXPECTED_KEYS.issubset(result.keys())
    assert result["material_group"] == material_group
    assert result["application_zone"] == application_zone
    assert isinstance(result["insert_identity"], dict)
    assert isinstance(result["risk_flags"], list)
