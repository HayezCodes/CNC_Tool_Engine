from grade_engine.catalog_review import filter_reviewed_catalog_records


def test_real_niagara_cutter_reviewed_records_load_through_viewer_helper() -> None:
    records = filter_reviewed_catalog_records(brand="Niagara Cutter")

    assert len(records) == 5
    assert all(record["verification_status"] == "reviewed_family_level" for record in records)
    assert all(record["cutting_data_status"] == "not_imported" for record in records)
    assert all(record["tool_category"] == "endmill" for record in records)
    assert any("roughing" in record["operation_fit"] for record in records)
    assert any("finishing" in record["operation_fit"] for record in records)
