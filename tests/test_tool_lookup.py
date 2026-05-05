from tool_lookup.cross_reference import cross_reference_tool
from tool_lookup.index import load_lookup_records
from tool_lookup.normalize import normalize_tool_number


def test_normalize_tool_number_removes_spaces_hyphens_and_case() -> None:
    assert normalize_tool_number("CNMG 432-PF 4425") == "CNMG432PF4425"
    assert normalize_tool_number("cnmg432 pf") == "CNMG432PF"
    assert normalize_tool_number("CoroMill 490") == "COROMILL490"
    assert normalize_tool_number("16ER AG60") == "16ERAG60"


def test_normalize_tool_number_handles_empty_and_none() -> None:
    assert normalize_tool_number("") == ""
    assert normalize_tool_number(None) == ""


def test_load_lookup_records_returns_rows() -> None:
    records = load_lookup_records()
    assert records
    assert any(record["tool_category"] == "turning_insert" for record in records)


def test_cross_reference_tool_returns_required_keys() -> None:
    result = cross_reference_tool("CoroMill 490")
    assert set(result.keys()) == {"query", "normalized_query", "exact_match", "alternatives", "warnings"}


def test_cross_reference_tool_unknown_search_warns_without_crashing() -> None:
    result = cross_reference_tool("ZZZ9999UNKNOWN")
    assert result["exact_match"] is None
    assert isinstance(result["alternatives"], list)
    assert result["warnings"]


def test_cross_reference_tool_known_series_returns_exact_match() -> None:
    result = cross_reference_tool("CoroMill 490")
    assert result["exact_match"] is not None
    assert result["exact_match"]["series"] == "CoroMill 490"


def test_cross_reference_tool_family_search_returns_alternatives() -> None:
    result = cross_reference_tool("CNMG")
    assert isinstance(result["alternatives"], list)
    assert result["alternatives"]
