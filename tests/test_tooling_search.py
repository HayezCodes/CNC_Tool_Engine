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


# ── Sandvik Coromant / Kennametal / Seco searchability tests ─────────────────

def test_sandvik_coromant_records_are_searchable() -> None:
    records = search_tooling_records("Sandvik Coromant")

    assert records
    assert records[0]["brand"] == "Sandvik Coromant"


def test_sandvik_coromant_records_count() -> None:
    records = filter_tooling_records(
        load_tooling_records(),
        {"brand": "sandvik"},
    )

    assert len(records) >= 10


def test_kennametal_records_are_searchable() -> None:
    records = search_tooling_records("Kennametal")

    assert records
    assert records[0]["brand"] == "Kennametal"


def test_kennametal_records_count() -> None:
    records = filter_tooling_records(
        load_tooling_records(),
        {"brand": "kennametal"},
    )

    assert len(records) >= 10


def test_seco_records_are_searchable() -> None:
    records = search_tooling_records("Seco")

    assert records
    assert records[0]["brand"] == "Seco Tools"


def test_seco_records_count() -> None:
    records = filter_tooling_records(
        load_tooling_records(),
        {"brand": "seco"},
    )

    assert len(records) >= 8


def test_filter_by_operation_returns_correct_records() -> None:
    records = filter_tooling_records(
        load_tooling_records(),
        {"operation": "threading"},
    )

    assert records
    assert all("threading" in record["operation_fit"] for record in records)


def test_filter_by_tool_category_endmill_returns_endmills_only() -> None:
    records = filter_tooling_records(
        load_tooling_records(),
        {"tool_category": "endmill"},
    )

    assert records
    assert all(record["tool_category"] == "endmill" for record in records)


def test_filter_by_grooving_insert_returns_grooving_only() -> None:
    records = filter_tooling_records(
        load_tooling_records(),
        {"tool_category": "grooving_insert"},
    )

    assert records
    assert all(record["tool_category"] == "grooving_insert" for record in records)


def test_explain_sandvik_match_includes_brand_reason() -> None:
    records = search_tooling_records("Sandvik Coromant")
    assert records
    reasons = explain_tool_match(records[0], "Sandvik Coromant")

    assert any("brand" in reason or "sandvik" in reason.lower() for reason in reasons)


def test_explain_kennametal_match_includes_brand_reason() -> None:
    records = search_tooling_records("Kennametal")
    assert records
    reasons = explain_tool_match(records[0], "Kennametal")

    assert any("brand" in reason or "kennametal" in reason.lower() for reason in reasons)


def test_no_feeds_or_speeds_in_new_brand_records() -> None:
    forbidden = {"sfm", "rpm", "feed", "feeds", "speed", "speeds", "ipr", "ipm", "fz", "vc"}
    for record in load_tooling_records():
        if record["brand"] in {"Sandvik Coromant", "Kennametal", "Seco Tools"}:
            record_keys = {k.lower() for k in record}
            assert not record_keys.intersection(forbidden), (
                f"Forbidden field in {record['brand']} record {record['manufacturer_part_number']}"
            )


def test_all_new_brand_records_have_not_imported_cutting_data_status() -> None:
    new_brands = {"Sandvik Coromant", "Kennametal", "Seco Tools"}
    for record in load_tooling_records():
        if record["brand"] in new_brands:
            assert record["cutting_data_status"] == "not_imported", (
                f"Unexpected cutting_data_status in {record['brand']} {record['manufacturer_part_number']}"
            )


def test_total_record_count_includes_all_brands() -> None:
    records = load_tooling_records()

    brands = {r["brand"] for r in records}
    assert "Sandvik Coromant" in brands
    assert "Kennametal" in brands
    assert "Seco Tools" in brands
    assert len(records) >= 30
