"""Tests for the Mitsubishi Materials structured JSON adapter.

Covers:
- Inline JSON parsing (no file I/O required)
- Sample fixture file integration
- Forbidden feed/speed key rejection
- Schema field completeness
- List field normalization
- Source metadata preservation
- verification_status and cutting_data_status enforcement
- Importer validation bridge
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from grade_engine.tooling_search import SCHEMA_FIELDS
from tools.import_tooling_records import validate_import_rows
from tools.tooling_adapters.base_adapter import (
    DEFAULT_CUTTING_DATA_STATUS,
    DEFAULT_VERIFICATION_STATUS,
    VALID_VERIFICATION_STATUSES,
)
from tools.tooling_adapters.mitsubishi_materials_adapter import (
    MitsubishiMaterialsAdapter,
    parse_mitsubishi_file,
)


SAMPLE_JSON_PATH = (
    Path(__file__).resolve().parent.parent
    / "tools"
    / "tooling_adapters"
    / "samples"
    / "sample_mitsubishi_materials_structured.json"
)
EXPECTED_RECORD_COUNT = 7


# ── Helpers ───────────────────────────────────────────────────────────────────

def _minimal_json(tool_records_json: str = "[]") -> str:
    return json.dumps({
        "catalog_header": {
            "manufacturer": "Mitsubishi Materials Corporation",
            "catalog_label": "Test Catalog",
            "catalog_url": "https://example.com/mmc",
        },
        "tool_records": json.loads(tool_records_json),
    })


def _make_record(
    part_number: str = "TEST-MMC-001",
    tool_type: str = "TurningInsert",
    materials: list[str] | None = None,
    operations: list[str] | None = None,
    extra_fields: dict | None = None,
) -> dict:
    record: dict = {
        "part_number": part_number,
        "tool_type": tool_type,
        "series": "Test Series",
        "family_name": "Test family",
        "designation": "CNMG 120408",
        "grade": "TEST-GRADE",
        "chipbreaker": "TEST-CB",
        "coating": "TEST-COAT",
        "material_groups": materials if materials is not None else ["P", "M"],
        "operations": operations if operations is not None else ["ExternalTurning"],
        "geometry_tags": ["NegativeRake"],
        "holder_compatibility": "Test holder",
        "coolant": "VerifyByCatalog",
        "source_page": "p.1",
        "notes": "Synthetic adapter fixture for parser testing; not manufacturer catalog data.",
    }
    if extra_fields:
        record.update(extra_fields)
    return record


# ── MitsubishiMaterialsAdapter unit tests ────────────────────────────────────

class TestMitsubishiAdapterInlineJson:

    def setup_method(self) -> None:
        self.adapter = MitsubishiMaterialsAdapter()

    def test_empty_tool_records_returns_empty_list(self) -> None:
        records = self.adapter.parse_json_string(_minimal_json("[]"))

        assert records == []
        assert self.adapter.rejected_count == 0
        assert self.adapter.parse_errors == []

    def test_single_valid_record_parses(self) -> None:
        raw = [_make_record()]
        records = self.adapter.parse_json_string(_minimal_json(json.dumps(raw)))

        assert len(records) == 1
        assert self.adapter.rejected_count == 0

    def test_brand_always_set_from_header(self) -> None:
        raw = [_make_record()]
        records = self.adapter.parse_json_string(_minimal_json(json.dumps(raw)))

        assert records[0]["brand"] == "Mitsubishi Materials Corporation"

    def test_brand_falls_back_to_constant_when_header_empty(self) -> None:
        data = json.dumps({
            "catalog_header": {"manufacturer": "", "catalog_label": "L", "catalog_url": "U"},
            "tool_records": [_make_record()],
        })
        records = self.adapter.parse_json_string(data)

        assert records[0]["brand"] == "Mitsubishi Materials Corporation"

    def test_all_schema_fields_present(self) -> None:
        raw = [_make_record()]
        records = self.adapter.parse_json_string(_minimal_json(json.dumps(raw)))

        for field in SCHEMA_FIELDS:
            assert field in records[0], f"Missing schema field: {field}"

    def test_cutting_data_status_always_not_imported(self) -> None:
        raw = [_make_record()]
        records = self.adapter.parse_json_string(_minimal_json(json.dumps(raw)))

        assert records[0]["cutting_data_status"] == "not_imported"

    def test_verification_status_is_valid(self) -> None:
        raw = [_make_record()]
        records = self.adapter.parse_json_string(_minimal_json(json.dumps(raw)))

        assert records[0]["verification_status"] in VALID_VERIFICATION_STATUSES

    def test_verification_status_default_value(self) -> None:
        raw = [_make_record()]
        records = self.adapter.parse_json_string(_minimal_json(json.dumps(raw)))

        assert records[0]["verification_status"] == DEFAULT_VERIFICATION_STATUS

    def test_dimensions_always_empty_dict(self) -> None:
        raw = [_make_record()]
        records = self.adapter.parse_json_string(_minimal_json(json.dumps(raw)))

        assert records[0]["dimensions"] == {}

    def test_source_label_preserved(self) -> None:
        raw = [_make_record()]
        records = self.adapter.parse_json_string(_minimal_json(json.dumps(raw)))

        assert records[0]["source_label"] == "Test Catalog"

    def test_source_url_preserved(self) -> None:
        raw = [_make_record()]
        records = self.adapter.parse_json_string(_minimal_json(json.dumps(raw)))

        assert records[0]["source_url"] == "https://example.com/mmc"

    def test_source_page_reference_preserved(self) -> None:
        raw = [_make_record()]
        records = self.adapter.parse_json_string(_minimal_json(json.dumps(raw)))

        assert records[0]["source_page_reference"] == "p.1"

    def test_material_fit_normalized_to_iso_codes(self) -> None:
        raw = [_make_record(materials=["P", "M", "K", "invalid_group"])]
        records = self.adapter.parse_json_string(_minimal_json(json.dumps(raw)))

        assert set(records[0]["material_fit"]) == {"P", "M", "K"}
        assert "invalid_group" not in records[0]["material_fit"]

    def test_material_fit_is_list(self) -> None:
        raw = [_make_record(materials=["P", "S"])]
        records = self.adapter.parse_json_string(_minimal_json(json.dumps(raw)))

        assert isinstance(records[0]["material_fit"], list)

    def test_operation_fit_is_list(self) -> None:
        raw = [_make_record(operations=["ExternalTurning", "Facing"])]
        records = self.adapter.parse_json_string(_minimal_json(json.dumps(raw)))

        assert isinstance(records[0]["operation_fit"], list)

    def test_operation_fit_maps_to_snake_case(self) -> None:
        raw = [_make_record(operations=["ExternalTurning", "ShoulderMilling"])]
        records = self.adapter.parse_json_string(_minimal_json(json.dumps(raw)))

        assert "external_turning" in records[0]["operation_fit"]
        assert "shoulder_milling" in records[0]["operation_fit"]

    def test_geometry_tags_is_list(self) -> None:
        raw = [_make_record()]
        records = self.adapter.parse_json_string(_minimal_json(json.dumps(raw)))

        assert isinstance(records[0]["geometry_tags"], list)

    def test_geometry_tags_normalized_to_snake_case(self) -> None:
        raw = [_make_record()]
        raw[0]["geometry_tags"] = ["NegativeRake", "80DegreeDiamond"]
        records = self.adapter.parse_json_string(_minimal_json(json.dumps(raw)))

        assert "negativerake" in records[0]["geometry_tags"]
        assert "80degreediamond" in records[0]["geometry_tags"]

    def test_holder_compatibility_is_list(self) -> None:
        raw = [_make_record()]
        records = self.adapter.parse_json_string(_minimal_json(json.dumps(raw)))

        assert isinstance(records[0]["holder_compatibility"], list)

    def test_coolant_through_coolant_maps_correctly(self) -> None:
        raw = [_make_record()]
        raw[0]["coolant"] = "ThroughCoolantCapable"
        records = self.adapter.parse_json_string(_minimal_json(json.dumps(raw)))

        assert records[0]["coolant_capability"] == "through_coolant_capable"

    def test_coolant_verify_by_catalog_maps_correctly(self) -> None:
        raw = [_make_record()]
        raw[0]["coolant"] = "VerifyByCatalog"
        records = self.adapter.parse_json_string(_minimal_json(json.dumps(raw)))

        assert records[0]["coolant_capability"] == "verify_by_catalog"

    def test_coolant_unknown_maps_to_unknown(self) -> None:
        raw = [_make_record()]
        raw[0]["coolant"] = "Unknown"
        records = self.adapter.parse_json_string(_minimal_json(json.dumps(raw)))

        assert records[0]["coolant_capability"] == "unknown"

    def test_tool_category_turning_insert_maps_correctly(self) -> None:
        raw = [_make_record(tool_type="TurningInsert")]
        records = self.adapter.parse_json_string(_minimal_json(json.dumps(raw)))

        assert records[0]["tool_category"] == "turning_insert"

    def test_tool_category_solid_carbide_endmill_maps_correctly(self) -> None:
        raw = [_make_record(tool_type="SolidCarbideEndmill")]
        records = self.adapter.parse_json_string(_minimal_json(json.dumps(raw)))

        assert records[0]["tool_category"] == "endmill"

    def test_tool_category_indexable_drill_maps_correctly(self) -> None:
        raw = [_make_record(tool_type="IndexableDrill")]
        records = self.adapter.parse_json_string(_minimal_json(json.dumps(raw)))

        assert records[0]["tool_category"] == "indexable_drill"

    def test_tool_category_grooving_insert_maps_correctly(self) -> None:
        raw = [_make_record(tool_type="GroovingInsert")]
        records = self.adapter.parse_json_string(_minimal_json(json.dumps(raw)))

        assert records[0]["tool_category"] == "grooving_insert"

    def test_tool_category_threading_insert_maps_correctly(self) -> None:
        raw = [_make_record(tool_type="ThreadingInsert")]
        records = self.adapter.parse_json_string(_minimal_json(json.dumps(raw)))

        assert records[0]["tool_category"] == "threading_insert"

    def test_invalid_json_returns_empty_with_error(self) -> None:
        records = self.adapter.parse_json_string("not valid json {{")

        assert records == []
        assert self.adapter.rejected_count == 0
        assert any("JSON parse error" in e for e in self.adapter.parse_errors)

    def test_top_level_array_returns_error(self) -> None:
        records = self.adapter.parse_json_string("[1, 2, 3]")

        assert records == []
        assert self.adapter.parse_errors

    def test_missing_tool_records_key_returns_error(self) -> None:
        data = json.dumps({"catalog_header": {}, "wrong_key": []})
        records = self.adapter.parse_json_string(data)

        assert records == []
        assert any("tool_records" in e for e in self.adapter.parse_errors)

    def test_forbidden_feed_rate_key_rejects_record(self) -> None:
        raw = [_make_record(extra_fields={"feedRate": "0.15"})]
        records = self.adapter.parse_json_string(_minimal_json(json.dumps(raw)))

        assert len(records) == 0
        assert self.adapter.rejected_count == 1
        assert any("feedRate" in e or "feed" in e.lower() for e in self.adapter.parse_errors)

    def test_forbidden_speed_key_rejects_record(self) -> None:
        raw = [_make_record(extra_fields={"cutting_speed_vc": 250})]
        records = self.adapter.parse_json_string(_minimal_json(json.dumps(raw)))

        assert len(records) == 0
        assert self.adapter.rejected_count == 1

    def test_forbidden_rpm_key_rejects_record(self) -> None:
        raw = [_make_record(extra_fields={"rpm_recommendation": 1800})]
        records = self.adapter.parse_json_string(_minimal_json(json.dumps(raw)))

        assert len(records) == 0
        assert self.adapter.rejected_count == 1

    def test_clean_record_not_rejected(self) -> None:
        raw = [_make_record()]
        records = self.adapter.parse_json_string(_minimal_json(json.dumps(raw)))

        assert len(records) == 1
        assert self.adapter.rejected_count == 0

    def test_forbidden_record_does_not_block_clean_records(self) -> None:
        raw = [
            _make_record(part_number="CLEAN-001"),
            _make_record(part_number="BAD-002", extra_fields={"sfm_data": 400}),
            _make_record(part_number="CLEAN-003"),
        ]
        records = self.adapter.parse_json_string(_minimal_json(json.dumps(raw)))

        assert len(records) == 2
        assert self.adapter.rejected_count == 1
        mpns = [r["manufacturer_part_number"] for r in records]
        assert "CLEAN-001" in mpns
        assert "CLEAN-003" in mpns
        assert "BAD-002" not in mpns

    def test_no_forbidden_keys_in_output(self) -> None:
        raw = [_make_record()]
        records = self.adapter.parse_json_string(_minimal_json(json.dumps(raw)))

        forbidden_terms = ("feed", "speed", "sfm", "rpm", "ipr", "ipm", "vc", "fz")
        for record in records:
            for key in record:
                for term in forbidden_terms:
                    assert term not in key.lower(), f"Forbidden term '{term}' in output key '{key}'"

    def test_validate_output_passes_for_valid_records(self) -> None:
        raw = [_make_record()]
        records = self.adapter.parse_json_string(_minimal_json(json.dumps(raw)))

        errors = self.adapter.validate_output(records)
        assert errors == []

    def test_parse_resets_state_between_calls(self) -> None:
        bad = [_make_record(extra_fields={"feedRate": "0.2"})]
        self.adapter.parse_json_string(_minimal_json(json.dumps(bad)))
        assert self.adapter.rejected_count == 1

        good = [_make_record()]
        records = self.adapter.parse_json_string(_minimal_json(json.dumps(good)))
        assert self.adapter.rejected_count == 0
        assert len(records) == 1

    def test_importer_validation_passes_for_valid_record(self) -> None:
        raw = [_make_record()]
        records = self.adapter.parse_json_string(_minimal_json(json.dumps(raw)))

        errors = validate_import_rows(records)
        assert errors == [], f"Importer validation errors: {errors}"


# ── Sample file integration tests ─────────────────────────────────────────────

class TestSampleFileIntegration:

    def setup_method(self) -> None:
        self.adapter = MitsubishiMaterialsAdapter()

    def test_sample_file_exists(self) -> None:
        assert SAMPLE_JSON_PATH.exists(), f"Sample fixture not found: {SAMPLE_JSON_PATH}"

    def test_sample_parses_without_errors(self) -> None:
        records = self.adapter.parse(SAMPLE_JSON_PATH)

        assert self.adapter.parse_errors == [], f"Parse errors: {self.adapter.parse_errors}"

    def test_sample_produces_expected_record_count(self) -> None:
        records = self.adapter.parse(SAMPLE_JSON_PATH)

        assert len(records) == EXPECTED_RECORD_COUNT

    def test_sample_no_rejected_records(self) -> None:
        self.adapter.parse(SAMPLE_JSON_PATH)

        assert self.adapter.rejected_count == 0

    def test_sample_all_records_have_all_schema_fields(self) -> None:
        records = self.adapter.parse(SAMPLE_JSON_PATH)

        for record in records:
            for field in SCHEMA_FIELDS:
                assert field in record, f"Missing field '{field}' in {record.get('manufacturer_part_number', '?')}"

    def test_sample_all_brands_are_mitsubishi(self) -> None:
        records = self.adapter.parse(SAMPLE_JSON_PATH)

        for record in records:
            assert record["brand"] == "Mitsubishi Materials Corporation"

    def test_sample_cutting_data_status_always_not_imported(self) -> None:
        records = self.adapter.parse(SAMPLE_JSON_PATH)

        for record in records:
            assert record["cutting_data_status"] == "not_imported"

    def test_sample_verification_status_all_valid(self) -> None:
        records = self.adapter.parse(SAMPLE_JSON_PATH)

        for record in records:
            assert record["verification_status"] in VALID_VERIFICATION_STATUSES

    def test_sample_dimensions_always_empty(self) -> None:
        records = self.adapter.parse(SAMPLE_JSON_PATH)

        for record in records:
            assert record["dimensions"] == {}

    def test_sample_source_label_present(self) -> None:
        records = self.adapter.parse(SAMPLE_JSON_PATH)

        for record in records:
            assert record["source_label"], f"Empty source_label in {record['manufacturer_part_number']}"

    def test_sample_source_url_present(self) -> None:
        records = self.adapter.parse(SAMPLE_JSON_PATH)

        for record in records:
            assert record["source_url"], f"Empty source_url in {record['manufacturer_part_number']}"

    def test_sample_list_fields_are_lists(self) -> None:
        records = self.adapter.parse(SAMPLE_JSON_PATH)

        for record in records:
            assert isinstance(record["material_fit"], list)
            assert isinstance(record["operation_fit"], list)
            assert isinstance(record["geometry_tags"], list)
            assert isinstance(record["holder_compatibility"], list)

    def test_sample_material_fit_only_iso_codes(self) -> None:
        valid = {"P", "M", "K", "N", "S", "H"}
        records = self.adapter.parse(SAMPLE_JSON_PATH)

        for record in records:
            for mat in record["material_fit"]:
                assert mat in valid, f"Non-ISO code '{mat}' in {record['manufacturer_part_number']}"

    def test_sample_no_forbidden_keys_in_output(self) -> None:
        records = self.adapter.parse(SAMPLE_JSON_PATH)
        forbidden_terms = ("feed", "speed", "sfm", "rpm", "ipr", "ipm")

        for record in records:
            for key in record:
                for term in forbidden_terms:
                    assert term not in key.lower(), (
                        f"Forbidden term '{term}' in key '{key}' of {record.get('manufacturer_part_number', '?')}"
                    )

    def test_sample_covers_expected_tool_categories(self) -> None:
        records = self.adapter.parse(SAMPLE_JSON_PATH)
        categories = {r["tool_category"] for r in records}

        assert "turning_insert" in categories
        assert "milling_insert" in categories
        assert "endmill" in categories
        assert "indexable_drill" in categories
        assert "grooving_insert" in categories
        assert "threading_insert" in categories

    def test_sample_passes_validate_adapter_output(self) -> None:
        records = self.adapter.parse(SAMPLE_JSON_PATH)
        errors = self.adapter.validate_output(records)

        assert errors == [], f"Adapter validation errors: {errors}"

    def test_sample_passes_importer_validation(self) -> None:
        records = self.adapter.parse(SAMPLE_JSON_PATH)
        errors = validate_import_rows(records)

        assert errors == [], f"Importer validation errors: {errors}"

    def test_parse_gtc_file_convenience_function(self) -> None:
        result = parse_mitsubishi_file(SAMPLE_JSON_PATH)

        assert result["record_count"] == EXPECTED_RECORD_COUNT
        assert result["rejected_count"] == 0
        assert result["parse_errors"] == []
        assert result["validation_errors"] == []
        assert len(result["records"]) == EXPECTED_RECORD_COUNT

    def test_sample_notes_contain_fixture_marker(self) -> None:
        records = self.adapter.parse(SAMPLE_JSON_PATH)

        for record in records:
            assert "fixture" in record["notes"].lower() or "synthetic" in record["notes"].lower(), (
                f"Fixture marker missing in notes for {record['manufacturer_part_number']}"
            )
