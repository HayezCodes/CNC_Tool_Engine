from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.review_tooling_records import (
    ALLOWED_REVIEW_STATUSES,
    batch_review_records,
    load_reviewed_tooling_records,
    load_tooling_records_for_review,
    promote_record_for_review,
    save_reviewed_tooling_records,
    validate_record_for_review,
)


def _make_valid_record(**overrides) -> dict:
    base = {
        "brand": "Test Brand",
        "tool_category": "turning_insert",
        "manufacturer_part_number": "TEST-MPN-001",
        "series": "Test Series",
        "family_name": "Test Family",
        "designation": "CNMG 120408",
        "grade": "",
        "chipbreaker": "",
        "coating": "",
        "material_fit": ["P", "M"],
        "operation_fit": ["external_turning", "facing"],
        "geometry_tags": ["turning_insert"],
        "dimensions": {},
        "holder_compatibility": [],
        "coolant_capability": "unknown",
        "source_label": "Test Catalog 2025",
        "source_url": "https://example.com/catalog",
        "source_page_reference": "",
        "verification_status": "sample_family_level_not_catalog_verified",
        "cutting_data_status": "not_imported",
        "notes": "Test record.",
    }
    base.update(overrides)
    return base


def _write_json(path: Path, data) -> Path:
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


# ── load_tooling_records_for_review ──────────────────────────────────────────

def test_load_tooling_records_for_review_loads_json(tmp_path: Path) -> None:
    records = [_make_valid_record()]
    path = _write_json(tmp_path / "records.json", records)
    loaded = load_tooling_records_for_review(path)
    assert len(loaded) == 1
    assert loaded[0]["brand"] == "Test Brand"


def test_load_tooling_records_for_review_rejects_non_array(tmp_path: Path) -> None:
    path = _write_json(tmp_path / "bad.json", {"key": "value"})
    with pytest.raises(ValueError, match="JSON array"):
        load_tooling_records_for_review(path)


# ── validate_record_for_review ────────────────────────────────────────────────

def test_validate_record_accepts_valid_record() -> None:
    record = _make_valid_record()
    errors = validate_record_for_review(record, "reviewed_exact_tool_candidate")
    assert errors == []


def test_validate_record_rejects_invalid_review_status() -> None:
    record = _make_valid_record()
    errors = validate_record_for_review(record, "bad_status")
    assert any("not allowed" in err for err in errors)


def test_validate_record_rejects_missing_source_label() -> None:
    record = _make_valid_record(source_label="")
    errors = validate_record_for_review(record, "reviewed_exact_tool_candidate")
    assert any("source_label" in err for err in errors)


def test_validate_record_rejects_missing_source_url() -> None:
    record = _make_valid_record(source_url="")
    errors = validate_record_for_review(record, "reviewed_exact_tool_candidate")
    assert any("source_url" in err for err in errors)


def test_validate_record_rejects_forbidden_feed_field() -> None:
    record = _make_valid_record()
    record["sfm"] = 400
    errors = validate_record_for_review(record, "reviewed_exact_tool_candidate")
    assert any("forbidden" in err.lower() for err in errors)


def test_validate_record_rejects_forbidden_speed_field() -> None:
    record = _make_valid_record()
    record["cutting_speed"] = 200
    errors = validate_record_for_review(record, "reviewed_family_level_candidate")
    assert any("forbidden" in err.lower() for err in errors)


def test_validate_record_rejects_non_not_imported_cutting_data_status() -> None:
    record = _make_valid_record(cutting_data_status="feeds_imported")
    errors = validate_record_for_review(record, "reviewed_exact_tool_candidate")
    assert any("not_imported" in err for err in errors)


def test_validate_both_allowed_review_statuses() -> None:
    record = _make_valid_record()
    for status in ALLOWED_REVIEW_STATUSES:
        errors = validate_record_for_review(record, status)
        assert errors == [], f"Expected no errors for status {status}"


# ── promote_record_for_review ─────────────────────────────────────────────────

def test_promote_record_adds_reviewer_and_date() -> None:
    record = _make_valid_record()
    promoted = promote_record_for_review(
        record,
        review_status="reviewed_exact_tool_candidate",
        reviewer="Jane Smith",
        review_notes="Catalog verified against 2025 edition.",
    )
    assert promoted["reviewer"] == "Jane Smith"
    assert promoted["review_date"]
    assert promoted["review_notes"] == "Catalog verified against 2025 edition."


def test_promote_record_sets_verification_status() -> None:
    record = _make_valid_record()
    promoted = promote_record_for_review(
        record,
        review_status="reviewed_family_level_candidate",
        reviewer="J. Smith",
    )
    assert promoted["verification_status"] == "reviewed_family_level_candidate"


def test_promote_record_preserves_cutting_data_status_as_not_imported() -> None:
    record = _make_valid_record(cutting_data_status="not_imported")
    promoted = promote_record_for_review(
        record,
        review_status="reviewed_exact_tool_candidate",
        reviewer="J. Smith",
    )
    assert promoted["cutting_data_status"] == "not_imported"


def test_promote_record_preserves_source_label_and_url() -> None:
    record = _make_valid_record(
        source_label="Real Catalog 2025",
        source_url="https://example.com/real-catalog",
    )
    promoted = promote_record_for_review(
        record,
        review_status="reviewed_exact_tool_candidate",
        reviewer="J. Smith",
    )
    assert promoted["source_label"] == "Real Catalog 2025"
    assert promoted["source_url"] == "https://example.com/real-catalog"


def test_promote_record_preserves_list_fields_without_mutation() -> None:
    mat = ["P", "M"]
    ops = ["external_turning"]
    record = _make_valid_record(material_fit=mat, operation_fit=ops)
    promoted = promote_record_for_review(
        record,
        review_status="reviewed_exact_tool_candidate",
        reviewer="J. Smith",
    )
    assert promoted["material_fit"] == ["P", "M"]
    assert promoted["operation_fit"] == ["external_turning"]
    assert promoted["material_fit"] is not mat


def test_promote_record_accepts_custom_review_date() -> None:
    record = _make_valid_record()
    promoted = promote_record_for_review(
        record,
        review_status="reviewed_exact_tool_candidate",
        reviewer="J. Smith",
        review_date="2025-01-15",
    )
    assert promoted["review_date"] == "2025-01-15"


# ── batch_review_records ──────────────────────────────────────────────────────

def test_batch_review_promotes_all_valid_records() -> None:
    records = [
        _make_valid_record(manufacturer_part_number="MPN-001"),
        _make_valid_record(manufacturer_part_number="MPN-002"),
    ]
    promoted, errors = batch_review_records(
        records,
        review_status="reviewed_exact_tool_candidate",
        reviewer="Tester",
    )
    assert len(promoted) == 2
    assert errors == []


def test_batch_review_rejects_records_with_forbidden_fields() -> None:
    records = [
        _make_valid_record(manufacturer_part_number="MPN-001"),
        {**_make_valid_record(manufacturer_part_number="MPN-002"), "sfm": 300},
    ]
    promoted, errors = batch_review_records(
        records,
        review_status="reviewed_exact_tool_candidate",
        reviewer="Tester",
    )
    assert len(promoted) == 1
    assert len(errors) == 1
    assert "MPN-002" in errors[0]


def test_batch_review_rejects_invalid_review_status() -> None:
    records = [_make_valid_record()]
    promoted, errors = batch_review_records(
        records,
        review_status="nonsense_status",
        reviewer="Tester",
    )
    assert promoted == []
    assert errors


def test_batch_review_preserves_not_imported_on_all_promoted() -> None:
    records = [
        _make_valid_record(manufacturer_part_number=f"MPN-{i:03d}")
        for i in range(5)
    ]
    promoted, errors = batch_review_records(
        records,
        review_status="reviewed_family_level_candidate",
        reviewer="Tester",
    )
    assert errors == []
    assert all(r["cutting_data_status"] == "not_imported" for r in promoted)


# ── save_reviewed_tooling_records / load_reviewed_tooling_records ─────────────

def test_save_reviewed_writes_json(tmp_path: Path) -> None:
    promoted = [_make_valid_record()]
    output = tmp_path / "reviewed.json"
    written = save_reviewed_tooling_records("test_brand", promoted, output_path=output)
    assert written == output
    assert output.exists()
    loaded = json.loads(output.read_text(encoding="utf-8"))
    assert loaded == promoted


def test_save_reviewed_auto_names_file(tmp_path: Path) -> None:
    promoted = [_make_valid_record()]
    from tools.review_tooling_records import REVIEWED_DIR
    written = save_reviewed_tooling_records("test_brand", promoted, output_path=tmp_path / "out.json")
    assert written.exists()


def test_load_reviewed_tooling_records_returns_all(tmp_path: Path) -> None:
    records_a = [_make_valid_record(manufacturer_part_number="A-001")]
    records_b = [_make_valid_record(manufacturer_part_number="B-001")]
    _write_json(tmp_path / "a_reviewed_tooling_records.json", records_a)
    _write_json(tmp_path / "b_reviewed_tooling_records.json", records_b)
    loaded = load_reviewed_tooling_records(tmp_path)
    assert len(loaded) == 2
    mpns = {r["manufacturer_part_number"] for r in loaded}
    assert mpns == {"A-001", "B-001"}


def test_load_reviewed_tooling_records_empty_dir(tmp_path: Path) -> None:
    loaded = load_reviewed_tooling_records(tmp_path)
    assert loaded == []


def test_reviewed_records_have_reviewer_field(tmp_path: Path) -> None:
    record = _make_valid_record()
    promoted, _ = batch_review_records(
        [record],
        review_status="reviewed_exact_tool_candidate",
        reviewer="Quality Control",
    )
    output = tmp_path / "reviewed.json"
    save_reviewed_tooling_records("test_brand", promoted, output_path=output)
    loaded = load_reviewed_tooling_records(tmp_path)
    assert loaded[0]["reviewer"] == "Quality Control"
    assert loaded[0]["review_date"]
    assert loaded[0]["verification_status"] == "reviewed_exact_tool_candidate"
    assert loaded[0]["cutting_data_status"] == "not_imported"
    assert loaded[0]["source_label"] == "Test Catalog 2025"
    assert loaded[0]["source_url"] == "https://example.com/catalog"
