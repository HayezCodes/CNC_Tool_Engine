import json
import shutil
import uuid
from pathlib import Path

from grade_engine import catalog_review
from grade_engine.catalog_review import (
    filter_reviewed_catalog_records,
    get_reviewed_catalog_summary,
    load_reviewed_catalog_records,
)


def test_empty_reviewed_folder_returns_empty_list_safely(monkeypatch) -> None:
    reviewed_root = _local_temp_root()
    reviewed_root.mkdir()
    monkeypatch.setattr(catalog_review, "REVIEWED_ROOT", reviewed_root)

    try:
        assert load_reviewed_catalog_records() == []
    finally:
        shutil.rmtree(reviewed_root, ignore_errors=True)


def test_helper_ignores_gitkeep(monkeypatch) -> None:
    reviewed_root = _local_temp_root()
    reviewed_root.mkdir()
    (reviewed_root / ".gitkeep").write_text("\n", encoding="utf-8")
    monkeypatch.setattr(catalog_review, "REVIEWED_ROOT", reviewed_root)

    try:
        assert load_reviewed_catalog_records() == []
    finally:
        shutil.rmtree(reviewed_root, ignore_errors=True)


def test_wrong_verification_status_is_ignored(monkeypatch) -> None:
    reviewed_root = _local_temp_root()
    _write_reviewed_file(reviewed_root, [{**_reviewed_record(), "verification_status": "staged_unreviewed"}])
    monkeypatch.setattr(catalog_review, "REVIEWED_ROOT", reviewed_root)

    try:
        assert load_reviewed_catalog_records() == []
    finally:
        shutil.rmtree(reviewed_root, ignore_errors=True)


def test_records_containing_feed_speed_fields_are_ignored(monkeypatch) -> None:
    reviewed_root = _local_temp_root()
    _write_reviewed_file(reviewed_root, [{**_reviewed_record(), "sfm": "not allowed"}])
    monkeypatch.setattr(catalog_review, "REVIEWED_ROOT", reviewed_root)

    try:
        assert load_reviewed_catalog_records() == []
    finally:
        shutil.rmtree(reviewed_root, ignore_errors=True)


def test_summary_shape_is_stable(monkeypatch) -> None:
    reviewed_root = _local_temp_root()
    reviewed_root.mkdir()
    monkeypatch.setattr(catalog_review, "REVIEWED_ROOT", reviewed_root)

    try:
        assert get_reviewed_catalog_summary() == {
            "total_records": 0,
            "brands": [],
            "tool_categories": [],
            "materials": [],
            "operations": [],
        }
    finally:
        shutil.rmtree(reviewed_root, ignore_errors=True)


def test_filtering_by_brand_category_material_and_operation(monkeypatch) -> None:
    reviewed_root = _local_temp_root()
    records = [
        _reviewed_record(
            brand="Helical Solutions",
            tool_category="endmill",
            material_fit=["P", "M"],
            operation_fit=["dynamic_milling", "roughing"],
            family_name="Dynamic/adaptive milling end mill families",
        ),
        _reviewed_record(
            brand="Harvey Tool",
            tool_category="chamfer_mill",
            material_fit=["N"],
            operation_fit=["chamfer"],
            family_name="Chamfer mill families",
        ),
    ]
    _write_reviewed_file(reviewed_root, records)
    monkeypatch.setattr(catalog_review, "REVIEWED_ROOT", reviewed_root)

    try:
        filtered = filter_reviewed_catalog_records(
            brand="Helical Solutions",
            tool_category="endmill",
            material_group="P",
            operation="dynamic_milling",
        )

        assert len(filtered) == 1
        assert filtered[0]["family_name"] == "Dynamic/adaptive milling end mill families"
    finally:
        shutil.rmtree(reviewed_root, ignore_errors=True)


def test_summary_includes_values_from_temp_reviewed_data(monkeypatch) -> None:
    reviewed_root = _local_temp_root()
    _write_reviewed_file(reviewed_root, [_reviewed_record()])
    monkeypatch.setattr(catalog_review, "REVIEWED_ROOT", reviewed_root)

    try:
        summary = get_reviewed_catalog_summary()

        assert summary["total_records"] == 1
        assert summary["brands"] == ["Helical Solutions"]
        assert summary["tool_categories"] == ["endmill"]
        assert summary["materials"] == ["P"]
        assert summary["operations"] == ["dynamic_milling"]
    finally:
        shutil.rmtree(reviewed_root, ignore_errors=True)


def test_real_helical_reviewed_records_load_through_viewer_helper() -> None:
    records = filter_reviewed_catalog_records(brand="Helical Solutions")

    assert len(records) == 10
    assert all(record["verification_status"] == "reviewed_family_level" for record in records)
    assert all(record["cutting_data_status"] == "not_imported" for record in records)
    assert any(record["family_name"] == "Dynamic/adaptive milling end mill families" for record in records)


def test_real_harvey_reviewed_records_load_through_viewer_helper() -> None:
    records = filter_reviewed_catalog_records(brand="Harvey Tool")

    assert len(records) == 6
    assert all(record["verification_status"] == "reviewed_family_level" for record in records)
    assert all(record["cutting_data_status"] == "not_imported" for record in records)
    assert any(record["tool_category"] == "chamfer_mill" for record in records)
    assert any(record["tool_category"] == "thread_mill" for record in records)
    assert any(record["tool_category"] == "undercut_tool" for record in records)


def _write_reviewed_file(root: Path, records: list[dict]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "reviewed_records.json").write_text(json.dumps(records), encoding="utf-8")


def _reviewed_record(**overrides) -> dict:
    record = {
        "brand": "Helical Solutions",
        "source_label": "Helical Solutions 2025 Product Catalog",
        "source_url": "https://www.helicaltool.com/catalog-request",
        "source_type": "official_catalog_page",
        "tool_category": "endmill",
        "family_name": "Dynamic/adaptive milling end mill families",
        "operation_fit": ["dynamic_milling"],
        "material_fit": ["P"],
        "strategy_fit": ["dynamic", "adaptive"],
        "coating_or_grade": "verify coating family by catalog",
        "geometry_tags": ["dynamic_milling"],
        "dimension_summary": "family-level only",
        "catalog_number": "",
        "cutting_data_status": "not_imported",
        "verification_status": "reviewed_family_level",
        "review_notes": "Family-level review only.",
        "source_page_reference": "",
        "reviewer": "J. Hayes",
        "review_date": "2026-05-13",
    }
    record.update(overrides)
    return record


def _local_temp_root() -> Path:
    return Path.cwd() / f"pytest-cache-files-catalog-review-{uuid.uuid4().hex}"
