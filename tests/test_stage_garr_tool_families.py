import json
from pathlib import Path

from tools.catalog_ingestion import PROHIBITED_CUTTING_DATA_FIELDS, validate_staged_record
from tools.stage_garr_tool_families import OUTPUT_FILENAME, build_garr_tool_family_records


STAGED_FILE = Path("tool_data/catalog_ingestion/staged") / OUTPUT_FILENAME


def test_script_builds_records_without_validation_errors() -> None:
    records = build_garr_tool_family_records()

    assert records
    for record in records:
        assert validate_staged_record(record) == []


def test_staged_file_schema_is_valid() -> None:
    records = _load_staged_records()

    assert len(records) == 5
    for record in records:
        assert validate_staged_record(record) == []
        assert set(record.keys()) == {
            "brand",
            "source_label",
            "source_url",
            "source_type",
            "tool_category",
            "family_name",
            "operation_fit",
            "material_fit",
            "strategy_fit",
            "coating_or_grade",
            "geometry_tags",
            "dimension_summary",
            "catalog_number",
            "cutting_data_status",
            "verification_status",
            "review_notes",
            "source_page_reference",
        }


def test_all_records_are_garr_tool() -> None:
    assert {record["brand"] for record in _load_staged_records()} == {"Garr Tool"}


def test_all_records_are_staged_unreviewed() -> None:
    assert {record["verification_status"] for record in _load_staged_records()} == {"staged_unreviewed"}


def test_cutting_data_status_is_not_imported() -> None:
    assert {record["cutting_data_status"] for record in _load_staged_records()} == {"not_imported"}


def test_no_feed_speed_fields_exist() -> None:
    for record in _load_staged_records():
        field_names = {_normalize_key(key) for key in record.keys()}
        assert not field_names.intersection(PROHIBITED_CUTTING_DATA_FIELDS)


def test_no_catalog_numbers_or_source_page_references_were_invented() -> None:
    for record in _load_staged_records():
        assert record["catalog_number"] == ""
        assert record["source_page_reference"] == ""


def test_required_garr_tool_families_exist() -> None:
    records = _load_staged_records()
    operations = {operation for record in records for operation in record["operation_fit"]}
    strategies = {strategy for record in records for strategy in record["strategy_fit"]}

    assert all(record["tool_category"] == "endmill" for record in records)
    assert {"roughing", "finishing", "profiling"}.issubset(operations)
    assert {"high_performance", "high_efficiency", "surface_finish_priority"}.issubset(strategies)


def test_records_require_human_review_note() -> None:
    for record in _load_staged_records():
        assert "human catalog review" in record["review_notes"]


def _load_staged_records() -> list[dict]:
    return json.loads(STAGED_FILE.read_text(encoding="utf-8"))


def _normalize_key(value: object) -> str:
    return str(value).strip().lower().replace(" ", "_").replace("-", "_")
