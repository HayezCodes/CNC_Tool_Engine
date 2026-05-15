from grade_engine.catalog_review import filter_reviewed_catalog_records


def test_real_yg_1_reviewed_records_load_through_viewer_helper() -> None:
    records = filter_reviewed_catalog_records(brand="YG-1")

    assert len(records) == 6
    assert all(record["verification_status"] == "reviewed_family_level" for record in records)
    assert all(record["cutting_data_status"] == "not_imported" for record in records)
    assert any(record["tool_category"] == "endmill" for record in records)
    assert any(record["tool_category"] == "drill" for record in records)
    assert any(record["tool_category"] == "tap" for record in records)
