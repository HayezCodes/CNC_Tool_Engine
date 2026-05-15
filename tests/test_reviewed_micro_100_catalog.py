from grade_engine.catalog_review import filter_reviewed_catalog_records


def test_real_micro_100_reviewed_records_load_through_viewer_helper() -> None:
    records = filter_reviewed_catalog_records(brand="Micro 100")

    assert len(records) == 6
    assert all(record["verification_status"] == "reviewed_family_level" for record in records)
    assert all(record["cutting_data_status"] == "not_imported" for record in records)
    assert any(record["tool_category"] == "boring_bar" for record in records)
    assert any(record["tool_category"] == "grooving_tool" for record in records)
    assert any(record["tool_category"] == "threading_tool" for record in records)
