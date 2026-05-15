from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.audit_tooling_search_records import (
    VALID_CUTTING_DATA_STATUSES,
    VALID_VERIFICATION_STATUSES,
    audit_record,
    audit_tooling_search_records,
    write_audit_report,
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


def _write_records(tmp_path: Path, filename: str, records: list) -> Path:
    path = tmp_path / filename
    path.write_text(json.dumps(records), encoding="utf-8")
    return path


# ── audit_record unit tests ───────────────────────────────────────────────────

def test_audit_record_clean_record_has_no_issues() -> None:
    record = _make_valid_record()
    issues = audit_record(record, 0, "test.json")
    assert issues == []


def test_audit_record_detects_missing_schema_field() -> None:
    record = _make_valid_record()
    del record["grade"]
    issues = audit_record(record, 0, "test.json")
    assert any(i["issue_type"] == "missing_schema_fields" for i in issues)
    assert any("grade" in i["detail"] for i in issues)


def test_audit_record_detects_empty_brand() -> None:
    record = _make_valid_record(brand="")
    issues = audit_record(record, 0, "test.json")
    assert any(i["issue_type"] == "missing_required_value" and "brand" in i["detail"] for i in issues)


def test_audit_record_detects_empty_source_label() -> None:
    record = _make_valid_record(source_label="")
    issues = audit_record(record, 0, "test.json")
    assert any("source_label" in i["detail"] for i in issues)


def test_audit_record_detects_empty_source_url() -> None:
    record = _make_valid_record(source_url="")
    issues = audit_record(record, 0, "test.json")
    assert any("source_url" in i["detail"] for i in issues)


def test_audit_record_detects_invalid_verification_status() -> None:
    record = _make_valid_record(verification_status="made_up_status")
    issues = audit_record(record, 0, "test.json")
    assert any(i["issue_type"] == "invalid_verification_status" for i in issues)


def test_audit_record_accepts_all_valid_verification_statuses() -> None:
    for status in VALID_VERIFICATION_STATUSES:
        record = _make_valid_record(verification_status=status)
        issues = audit_record(record, 0, "test.json")
        assert not any(i["issue_type"] == "invalid_verification_status" for i in issues), status


def test_audit_record_detects_invalid_cutting_data_status() -> None:
    record = _make_valid_record(cutting_data_status="feeds_imported")
    issues = audit_record(record, 0, "test.json")
    assert any(i["issue_type"] == "invalid_cutting_data_status" for i in issues)


def test_audit_record_accepts_valid_cutting_data_statuses() -> None:
    for status in VALID_CUTTING_DATA_STATUSES:
        record = _make_valid_record(cutting_data_status=status)
        issues = audit_record(record, 0, "test.json")
        assert not any(i["issue_type"] == "invalid_cutting_data_status" for i in issues), status


def test_audit_record_detects_forbidden_sfm_field() -> None:
    record = _make_valid_record()
    record["sfm"] = 500
    issues = audit_record(record, 0, "test.json")
    assert any(i["issue_type"] == "forbidden_feed_speed_fields" for i in issues)


def test_audit_record_detects_forbidden_feed_field() -> None:
    record = _make_valid_record()
    record["feed_rate"] = 0.1
    issues = audit_record(record, 0, "test.json")
    assert any(i["issue_type"] == "forbidden_feed_speed_fields" for i in issues)


def test_audit_record_detects_forbidden_rpm_field() -> None:
    record = _make_valid_record()
    record["rpm"] = 2000
    issues = audit_record(record, 0, "test.json")
    assert any(i["issue_type"] == "forbidden_feed_speed_fields" for i in issues)


def test_audit_record_detects_invalid_list_field_type_material_fit() -> None:
    record = _make_valid_record(material_fit="P M K")
    issues = audit_record(record, 0, "test.json")
    assert any(i["issue_type"] == "invalid_list_field_type" and "material_fit" in i["detail"] for i in issues)


def test_audit_record_detects_invalid_list_field_type_operation_fit() -> None:
    record = _make_valid_record(operation_fit="external_turning")
    issues = audit_record(record, 0, "test.json")
    assert any(i["issue_type"] == "invalid_list_field_type" and "operation_fit" in i["detail"] for i in issues)


def test_audit_record_detects_empty_operation_fit() -> None:
    record = _make_valid_record(operation_fit=[])
    issues = audit_record(record, 0, "test.json")
    assert any(i["issue_type"] == "missing_operation_fit" for i in issues)


def test_audit_record_detects_empty_material_fit() -> None:
    record = _make_valid_record(material_fit=[])
    issues = audit_record(record, 0, "test.json")
    assert any(i["issue_type"] == "missing_material_fit" for i in issues)


# ── audit_tooling_search_records integration tests ────────────────────────────

def test_audit_detects_duplicate_mpn_within_brand(tmp_path: Path) -> None:
    records = [
        _make_valid_record(manufacturer_part_number="DUPE-MPN-001"),
        _make_valid_record(manufacturer_part_number="DUPE-MPN-001"),
    ]
    _write_records(tmp_path, "dupes.json", records)
    report = audit_tooling_search_records(tmp_path)
    assert any(i["issue_type"] == "duplicate_manufacturer_part_number" for i in report["issues"])


def test_audit_does_not_flag_same_mpn_different_brand(tmp_path: Path) -> None:
    records = [
        _make_valid_record(brand="Brand A", manufacturer_part_number="COMMON-MPN-001"),
        _make_valid_record(brand="Brand B", manufacturer_part_number="COMMON-MPN-001"),
    ]
    _write_records(tmp_path, "two_brands.json", records)
    report = audit_tooling_search_records(tmp_path)
    assert not any(i["issue_type"] == "duplicate_manufacturer_part_number" for i in report["issues"])


def test_audit_reports_correct_file_count(tmp_path: Path) -> None:
    _write_records(tmp_path, "file_a.json", [_make_valid_record(manufacturer_part_number="A-001")])
    _write_records(tmp_path, "file_b.json", [_make_valid_record(manufacturer_part_number="B-001")])
    report = audit_tooling_search_records(tmp_path)
    assert report["files_audited"] == 2


def test_audit_clean_dir_has_zero_issues(tmp_path: Path) -> None:
    _write_records(tmp_path, "clean.json", [_make_valid_record()])
    report = audit_tooling_search_records(tmp_path)
    assert report["total_issues"] == 0


def test_audit_handles_invalid_json_file(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{not valid json", encoding="utf-8")
    report = audit_tooling_search_records(tmp_path)
    assert any(i["issue_type"] == "json_parse_error" for i in report["issues"])


def test_audit_handles_non_array_json_file(tmp_path: Path) -> None:
    bad = tmp_path / "object.json"
    bad.write_text(json.dumps({"key": "value"}), encoding="utf-8")
    report = audit_tooling_search_records(tmp_path)
    assert any(i["issue_type"] == "invalid_file_format" for i in report["issues"])


def test_audit_real_records_dir_has_no_issues() -> None:
    report = audit_tooling_search_records()
    issue_types = {i["issue_type"] for i in report["issues"]}
    assert "forbidden_feed_speed_fields" not in issue_types
    assert "invalid_verification_status" not in issue_types
    assert "invalid_cutting_data_status" not in issue_types
    assert "duplicate_manufacturer_part_number" not in issue_types


def test_write_audit_report_creates_file(tmp_path: Path) -> None:
    _write_records(tmp_path, "sample.json", [_make_valid_record()])
    report = audit_tooling_search_records(tmp_path)
    output = tmp_path / "report.json"
    written = write_audit_report(report, output)
    assert written == output
    assert output.exists()
    loaded = json.loads(output.read_text(encoding="utf-8"))
    assert loaded["files_audited"] == 1
    assert "audit_date" in loaded
