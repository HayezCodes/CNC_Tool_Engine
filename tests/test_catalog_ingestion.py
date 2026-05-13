import json
import shutil
import uuid
from pathlib import Path

import pytest

from tools.catalog_ingestion import (
    build_staged_record,
    list_sources_by_brand,
    load_catalog_sources,
    save_staged_records,
    validate_staged_record,
)


REQUIRED_BRANDS = {
    "YG-1",
    "Helical Solutions",
    "Harvey Tool",
    "Micro 100",
    "Garr Tool",
    "Niagara Cutter",
    "Sumitomo Electric",
    "Kyocera",
    "Tungaloy",
    "Haas Tooling",
}


def test_source_registry_loads() -> None:
    sources = load_catalog_sources()

    assert sources
    assert isinstance(sources, list)


def test_required_brands_exist() -> None:
    brands = {source["brand"] for source in load_catalog_sources()}

    assert REQUIRED_BRANDS.issubset(brands)


def test_list_sources_by_brand_returns_matching_sources() -> None:
    sources = list_sources_by_brand("Helical")

    assert sources
    assert sources[0]["brand"] == "Helical Solutions"


def test_staged_record_builder_sets_safe_defaults() -> None:
    record = build_staged_record(
        brand="Helical Solutions",
        source_url="https://www.helicaltool.com/catalog-request",
        tool_category="endmill",
        family_name="High-performance endmill families",
    )

    assert record["cutting_data_status"] == "not_imported"
    assert record["verification_status"] == "staged_unreviewed"
    assert record["operation_fit"] == []
    assert validate_staged_record(record) == []


@pytest.mark.parametrize(
    "missing_field",
    ["brand", "source_url", "tool_category", "family_name"],
)
def test_staged_validation_rejects_missing_required_fields(missing_field: str) -> None:
    record = build_staged_record(
        brand="Helical Solutions",
        source_url="https://www.helicaltool.com/catalog-request",
        tool_category="endmill",
        family_name="High-performance endmill families",
    )
    record[missing_field] = ""

    errors = validate_staged_record(record)

    assert any(missing_field in error for error in errors)


@pytest.mark.parametrize("field_name", ["sfm", "rpm", "feed_per_tooth", "chip_load", "cutting_speed"])
def test_staged_validation_rejects_feeds_speeds_fields(field_name: str) -> None:
    record = build_staged_record(
        brand="Helical Solutions",
        source_url="https://www.helicaltool.com/catalog-request",
        tool_category="endmill",
        family_name="High-performance endmill families",
        **{field_name: "not allowed"},
    )

    errors = validate_staged_record(record)

    assert any("Exact feeds/speeds" in error for error in errors)


def test_catalog_number_requires_source_page_reference() -> None:
    record = build_staged_record(
        brand="Helical Solutions",
        source_url="https://www.helicaltool.com/catalog-request",
        tool_category="endmill",
        family_name="High-performance endmill families",
        catalog_number="ABC123",
    )

    errors = validate_staged_record(record)

    assert any("source_page_reference is required" in error for error in errors)


def test_save_staged_records_writes_json_to_staged_folder() -> None:
    temp_root = _local_temp_root()
    record = build_staged_record(
        brand="Helical Solutions",
        source_url="https://www.helicaltool.com/catalog-request",
        tool_category="endmill",
        family_name="High-performance endmill families",
        operation_fit=["dynamic_milling"],
        material_fit=["P"],
    )

    try:
        path = save_staged_records("Helical Solutions", [record], data_root=temp_root)
        saved = json.loads(path.read_text(encoding="utf-8"))

        assert path.name == "helical_solutions_staged_records.json"
        assert path.parent == temp_root / "catalog_ingestion" / "staged"
        assert saved == [record]
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def test_save_staged_records_rejects_invalid_records() -> None:
    temp_root = _local_temp_root()
    record = build_staged_record(
        brand="Helical Solutions",
        source_url="https://www.helicaltool.com/catalog-request",
        tool_category="",
        family_name="High-performance endmill families",
    )

    try:
        with pytest.raises(ValueError):
            save_staged_records("Helical Solutions", [record], data_root=temp_root)
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def _local_temp_root() -> Path:
    return Path.cwd() / f"pytest-cache-files-catalog-ingestion-{uuid.uuid4().hex}"
