from grade_engine.tooling_search import (
    SCHEMA_FIELDS,
    build_tooling_search_index,
    explain_tool_match,
    filter_tooling_records,
    load_tooling_records,
    search_tooling_records,
)


FORBIDDEN_FIELDS = {"sfm", "rpm", "feed", "feeds", "speed", "speeds"}


def test_records_load() -> None:
    records = load_tooling_records()

    assert records
    assert len(records) >= 5


def test_required_schema_fields_exist() -> None:
    for record in load_tooling_records():
        for field in SCHEMA_FIELDS:
            assert field in record


def test_search_by_brand_works() -> None:
    records = search_tooling_records("Sumitomo")

    assert records
    assert records[0]["brand"] == "Sumitomo Electric"


def test_search_by_designation_works() -> None:
    records = search_tooling_records("CNMG 120408")

    assert records
    assert any(record["designation"] == "CNMG 120408" for record in records)


def test_search_by_tool_category_works() -> None:
    turning_records = search_tooling_records("", {"tool_category": "turning_insert"})

    assert turning_records
    assert all(record["tool_category"] == "turning_insert" for record in turning_records)


def test_filters_work() -> None:
    records = filter_tooling_records(
        load_tooling_records(),
        {
            "brand": "Kyocera",
            "tool_category": "indexable_drill",
            "material_group": "P",
            "operation": "drilling",
        },
    )

    assert len(records) == 1
    assert records[0]["brand"] == "Kyocera"


def test_build_tooling_search_index_has_tokens() -> None:
    index = build_tooling_search_index(load_tooling_records())

    assert index["record_count"] >= 5
    assert "sumitomo" in index["token_index"]


def test_no_feeds_or_speeds_fields_exist() -> None:
    text = str(load_tooling_records()).lower()

    for forbidden in FORBIDDEN_FIELDS:
        assert forbidden not in text


def test_unverified_sample_records_are_clearly_marked() -> None:
    records = load_tooling_records()

    assert all(record["verification_status"] == "sample_family_level_not_catalog_verified" for record in records)
    assert all(record["cutting_data_status"] == "not_imported" for record in records)


def test_explain_tool_match_returns_transparent_reasons() -> None:
    record = search_tooling_records("CNMG 120408")[0]
    reasons = explain_tool_match(record, "CNMG 120408", {"tool_category": "turning_insert", "material_group": "P"})

    assert reasons
    assert any("designation" in reason or "tool category filter matched" in reason for reason in reasons)
