import json
import shutil
import uuid
from datetime import date
from pathlib import Path

import pytest

from tools import review_catalog_records
from tools.review_catalog_records import (
    load_staged_records,
    mark_record_reviewed,
    save_reviewed_records,
    summarize_staged_records,
    validate_reviewed_record,
)


STAGED_FILE = Path("tool_data/catalog_ingestion/staged/helical_solutions_endmill_families.json")


def test_staged_records_load() -> None:
    records = load_staged_records(STAGED_FILE)

    assert records
    assert all(record["brand"] == "Helical Solutions" for record in records)


def test_summary_includes_count_brands_categories_and_statuses() -> None:
    summary = summarize_staged_records(load_staged_records(STAGED_FILE))

    assert summary["total_records"] == 10
    assert summary["brands"] == ["Helical Solutions"]
    assert "endmill" in summary["tool_categories"]
    assert "staged_unreviewed" in summary["verification_statuses"]
    assert summary["cutting_data_statuses"] == ["not_imported"]
    assert "Dynamic/adaptive milling end mill families" in summary["family_names"]


def test_mark_record_reviewed_adds_review_metadata() -> None:
    record = load_staged_records(STAGED_FILE)[0]
    reviewed = mark_record_reviewed(record, reviewer="J. Hayes", notes="Family scope reviewed only.")

    assert reviewed["reviewer"] == "J. Hayes"
    assert reviewed["review_date"] == date.today().isoformat()
    assert reviewed["review_notes"] == "Family scope reviewed only."
    assert reviewed["verification_status"] == "reviewed_family_level"
    assert reviewed["cutting_data_status"] == "not_imported"


def test_reviewed_validation_rejects_missing_reviewer() -> None:
    reviewed = _reviewed_record()
    reviewed["reviewer"] = ""

    errors = validate_reviewed_record(reviewed)

    assert any("reviewer is required" in error for error in errors)


@pytest.mark.parametrize("field_name", ["sfm", "rpm", "feed_per_tooth", "chip_load", "cutting_speed"])
def test_reviewed_validation_rejects_feed_speed_fields(field_name: str) -> None:
    reviewed = _reviewed_record()
    reviewed[field_name] = "not allowed"

    errors = validate_reviewed_record(reviewed)

    assert any("Exact feeds/speeds" in error for error in errors)


def test_reviewed_validation_requires_source_page_reference_for_catalog_number() -> None:
    reviewed = _reviewed_record()
    reviewed["catalog_number"] = "ABC123"
    reviewed["source_page_reference"] = ""

    errors = validate_reviewed_record(reviewed)

    assert any("source_page_reference is required" in error for error in errors)


def test_save_reviewed_records_writes_to_reviewed_folder(monkeypatch) -> None:
    temp_root = Path.cwd() / f"pytest-cache-files-reviewed-{uuid.uuid4().hex}"
    reviewed_root = temp_root / "catalog_ingestion" / "reviewed"
    records = [_reviewed_record()]
    monkeypatch.setattr(review_catalog_records, "REVIEWED_ROOT", reviewed_root)

    try:
        path = save_reviewed_records("helical_solutions", records)
        saved = json.loads(path.read_text(encoding="utf-8"))

        assert path.parent == reviewed_root
        assert path.name == "helical_solutions_reviewed_records.json"
        assert saved == records
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def _reviewed_record() -> dict:
    return mark_record_reviewed(
        load_staged_records(STAGED_FILE)[0],
        reviewer="J. Hayes",
        notes="Family-level review only.",
    )
