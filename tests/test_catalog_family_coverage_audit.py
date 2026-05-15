import json
import shutil
import uuid
from pathlib import Path

from tools.audit_catalog_family_coverage import (
    EXPECTED_BRANDS,
    build_catalog_family_coverage_report,
    save_catalog_family_coverage_report,
)


FORBIDDEN_TERMS = {"sfm", "rpm", "feed_per_tooth", "chip_load", "cutting_speed", "surface_speed"}


def test_audit_runs() -> None:
    report = build_catalog_family_coverage_report()

    assert report["brands"]
    assert len(report["brands"]) == len(EXPECTED_BRANDS)


def test_all_expected_brands_appear() -> None:
    report = build_catalog_family_coverage_report()
    brands = {item["brand"] for item in report["brands"]}

    assert set(EXPECTED_BRANDS) == brands


def test_each_brand_has_at_least_one_reviewed_record() -> None:
    report = build_catalog_family_coverage_report()

    for item in report["brands"]:
        assert item["total_reviewed_records"] >= 1
        assert item["reviewed_file_path"]


def test_missing_category_list_exists_for_each_brand() -> None:
    report = build_catalog_family_coverage_report()

    for item in report["brands"]:
        assert "missing_obvious_family_categories" in item
        assert isinstance(item["missing_obvious_family_categories"], list)


def test_report_json_writes_successfully() -> None:
    temp_root = _local_temp_root()
    output_path = temp_root / "catalog_family_coverage_report.json"

    try:
        report = build_catalog_family_coverage_report()
        path = save_catalog_family_coverage_report(report, output_path=output_path)

        assert path == output_path
        saved = json.loads(path.read_text(encoding="utf-8"))
        assert {item["brand"] for item in saved["brands"]} == set(EXPECTED_BRANDS)
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def test_no_speeds_feeds_in_audit_output() -> None:
    report = build_catalog_family_coverage_report()
    text = json.dumps(report).lower()

    for forbidden in FORBIDDEN_TERMS:
        assert forbidden not in text


def _local_temp_root() -> Path:
    return Path.cwd() / f"pytest-cache-files-coverage-audit-{uuid.uuid4().hex}"
