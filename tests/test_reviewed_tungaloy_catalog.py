from grade_engine.catalog_review import filter_reviewed_catalog_records


def test_real_tungaloy_reviewed_records_load_through_viewer_helper() -> None:
    records = filter_reviewed_catalog_records(brand="Tungaloy")

    assert len(records) == 6
    assert all(record["verification_status"] == "reviewed_family_level" for record in records)
    assert all(record["cutting_data_status"] == "not_imported" for record in records)
    assert any(record["tool_category"] == "grooving_insert" for record in records)
    assert any(record["tool_category"] == "threading_insert" for record in records)
    assert any(record["tool_category"] == "indexable_cutter" for record in records)
    assert any(record["tool_category"] == "multifunction_tooling" for record in records)
