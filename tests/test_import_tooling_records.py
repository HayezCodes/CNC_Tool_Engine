from __future__ import annotations

from pathlib import Path

import pytest

from tools.import_tooling_records import import_tooling_records, load_import_rows, normalize_import_rows, validate_import_rows


TEMPLATE_PATH = Path("tool_data/tooling_search/tooling_records_template.csv")


def test_dry_run_import_succeeds_without_writing(tmp_path: Path) -> None:
    output_path = tmp_path / "imported.json"

    result = import_tooling_records(TEMPLATE_PATH, output_path=output_path, dry_run=True)

    assert result["dry_run"] is True
    assert result["record_count"] == 3
    assert result["normalized_record_count"] == 3
    assert result["errors"] == []
    assert not output_path.exists()


def test_required_field_validation_rejects_missing_value(tmp_path: Path) -> None:
    csv_path = tmp_path / "missing_brand.csv"
    csv_path.write_text(
        TEMPLATE_PATH.read_text(encoding="utf-8").replace("Helical Solutions", "", 1),
        encoding="utf-8",
    )

    result = import_tooling_records(csv_path, dry_run=True)

    assert result["errors"]
    assert any("required field 'brand' must not be empty" in error for error in result["errors"])


def test_list_normalization_works() -> None:
    rows = load_import_rows(TEMPLATE_PATH)
    normalized = normalize_import_rows(rows)

    assert normalized[0]["material_fit"] == ["P", "M", "K", "N", "S", "H"]
    assert normalized[0]["operation_fit"] == ["general_milling", "profiling", "roughing", "finishing"]
    assert normalized[1]["geometry_tags"] == ["turning_insert", "production_turning", "indexable_turning"]


def test_feed_speed_rejection_works(tmp_path: Path) -> None:
    csv_path = tmp_path / "forbidden_fields.csv"
    csv_path.write_text(
        "brand,tool_category,manufacturer_part_number,series,family_name,designation,grade,chipbreaker,coating,material_fit,operation_fit,geometry_tags,dimensions,holder_compatibility,coolant_capability,source_label,source_url,source_page_reference,verification_status,cutting_data_status,notes,sfm\n"
        'Test Brand,endmill,TEST-001,Series,Family,designation,,,,"P","general_milling","square_end",{},"",unknown,Source,https://example.com,,sample_family_level_not_catalog_verified,not_imported,Note,500\n',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Forbidden feed/speed fields present"):
        load_import_rows(csv_path)


def test_validate_import_rows_reports_missing_schema_field() -> None:
    rows = [
        {
            "brand": "Test Brand",
            "tool_category": "endmill",
        }
    ]

    errors = validate_import_rows(rows)

    assert errors
    assert any("missing required fields" in error for error in errors)
