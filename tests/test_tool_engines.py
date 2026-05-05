import pytest

from grade_engine.enums import APPLICATION_ZONES, MATERIAL_GROUPS
from grade_engine.tool_engines import (
    resolve_drilling_engine,
    resolve_endmill_engine,
    resolve_facemill_engine,
    resolve_grooving_engine,
    resolve_threading_engine,
)


EXPECTED_KEYS = {
    "tool_family",
    "recommendation_title",
    "recommendation_summary",
    "tool_direction",
    "geometry_hint",
    "risk_flags",
    "reasoning_steps",
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
def test_drilling_engine_smoke(material_group: str, application_zone: str) -> None:
    result = resolve_drilling_engine(
        {
            **make_input(material_group, application_zone),
            "drill_type": "Solid Carbide Drill",
            "diameter_mm": 12.0,
            "l_d_ratio": 5,
        }
    )

    assert EXPECTED_KEYS.issubset(result.keys())
    assert result["drill_type"] in {"Solid Carbide Drill", "Indexable Drill"}
    assert isinstance(result["risk_flags"], list)
    assert isinstance(result["reasoning_steps"], list)


@pytest.mark.parametrize("material_group", MATERIAL_GROUPS)
@pytest.mark.parametrize("application_zone", APPLICATION_ZONES)
def test_endmill_engine_smoke(material_group: str, application_zone: str) -> None:
    result = resolve_endmill_engine({**make_input(material_group, application_zone), "operation": "Profiling"})

    assert EXPECTED_KEYS.issubset(result.keys())
    assert result["tool_family"] == "Endmill"
    assert isinstance(result["risk_flags"], list)
    assert isinstance(result["reasoning_steps"], list)


@pytest.mark.parametrize("material_group", MATERIAL_GROUPS)
@pytest.mark.parametrize("application_zone", APPLICATION_ZONES)
def test_facemill_engine_smoke(material_group: str, application_zone: str) -> None:
    result = resolve_facemill_engine({**make_input(material_group, application_zone), "operation": "Facing"})

    assert EXPECTED_KEYS.issubset(result.keys())
    assert result["tool_family"] == "Face Mill"
    assert isinstance(result["risk_flags"], list)
    assert isinstance(result["reasoning_steps"], list)


@pytest.mark.parametrize("material_group", MATERIAL_GROUPS)
@pytest.mark.parametrize("application_zone", APPLICATION_ZONES)
def test_grooving_engine_smoke(material_group: str, application_zone: str) -> None:
    result = resolve_grooving_engine({**make_input(material_group, application_zone), "operation": "Grooving"})

    assert EXPECTED_KEYS.issubset(result.keys())
    assert result["tool_family"] == "Grooving Insert"
    assert isinstance(result["risk_flags"], list)
    assert isinstance(result["reasoning_steps"], list)


@pytest.mark.parametrize("material_group", MATERIAL_GROUPS)
@pytest.mark.parametrize("application_zone", APPLICATION_ZONES)
def test_threading_engine_smoke(material_group: str, application_zone: str) -> None:
    result = resolve_threading_engine(
        {
            **make_input(material_group, application_zone),
            "thread_type": "external_threading",
            "pitch_hint": "Medium",
        }
    )

    assert EXPECTED_KEYS.issubset(result.keys())
    assert result["tool_family"] == "Threading Insert"
    assert isinstance(result["risk_flags"], list)
    assert isinstance(result["reasoning_steps"], list)
