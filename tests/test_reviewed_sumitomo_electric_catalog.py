from grade_engine.catalog_review import filter_reviewed_catalog_records


def test_real_sumitomo_electric_reviewed_records_load_through_viewer_helper() -> None:
    records = filter_reviewed_catalog_records(brand="Sumitomo Electric")

    assert len(records) == 7
    assert all(record["verification_status"] == "reviewed_family_level" for record in records)
    assert all(record["cutting_data_status"] == "not_imported" for record in records)
    assert any(record["tool_category"] == "turning_insert" for record in records)
    assert any(record["tool_category"] == "milling_insert" for record in records)
    assert any(record["tool_category"] == "indexable_cutter" for record in records)
    assert any(record["tool_category"] == "indexable_drill" for record in records)
