"""Unit tests for the Guhring structured JSON adapter.

All tests use inline JSON or the synthetic fixture file — never real catalog data.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.tooling_adapters.guhring_adapter import GuhringAdapter, parse_guhring_file
from tools.import_tooling_records import validate_import_rows
from grade_engine.tooling_search import SCHEMA_FIELDS


SAMPLE_JSON_PATH = (
    Path(__file__).resolve().parent.parent
    / "tools" / "tooling_adapters" / "samples" / "sample_guhring_structured.json"
)
EXPECTED_RECORD_COUNT = 8


# ── Helpers ───────────────────────────────────────────────────────────────────

def _minimal_json(tool_records: list[dict] | None = None) -> str:
    return json.dumps({
        "catalog_header": {
            "manufacturer": "Guhring KG",
            "catalog_label": "Test Label",
            "catalog_url": "https://example.com",
        },
        "tool_records": tool_records if tool_records is not None else [],
    })


def _make_record(**overrides) -> dict:
    base = {
        "part_number": "FIXTURE-GUH-TEST-001",
        "tool_type": "SolidCarbideDrill",
        "series": "RT100U Series",
        "family_name": "Test drill family",
        "designation": "solid carbide drill 8mm",
        "grade": "",
        "chipbreaker": "",
        "coating": "FIXTURE-TiAlN",
        "material_groups": ["P", "M", "K"],
        "operations": ["Drilling", "ThroughHoleDrilling"],
        "geometry_tags": ["SolidCarbide", "ThroughCoolant"],
        "holder_compatibility": "Cylindrical shank",
        "coolant": "ThroughCoolantCapable",
        "source_page": "p.D-1",
        "notes": "Synthetic fixture for testing.",
    }
    base.update(overrides)
    return base


# ── Inline JSON tests ─────────────────────────────────────────────────────────

class TestGuhringAdapterInlineJson:
    def test_empty_tool_records_returns_empty_list(self) -> None:
        adapter = GuhringAdapter()
        records = adapter.parse_json_string(_minimal_json([]))
        assert records == []
        assert adapter.parse_errors == []

    def test_single_valid_record_parses(self) -> None:
        adapter = GuhringAdapter()
        records = adapter.parse_json_string(_minimal_json([_make_record()]))
        assert len(records) == 1
        assert adapter.parse_errors == []

    def test_brand_always_set_from_header(self) -> None:
        adapter = GuhringAdapter()
        records = adapter.parse_json_string(_minimal_json([_make_record()]))
        assert records[0]["brand"] == "Guhring KG"

    def test_brand_falls_back_to_constant_when_header_empty(self) -> None:
        data = {
            "catalog_header": {"manufacturer": "", "catalog_label": "L", "catalog_url": "U"},
            "tool_records": [_make_record()],
        }
        adapter = GuhringAdapter()
        records = adapter.parse_json_string(json.dumps(data))
        assert records[0]["brand"] == "Guhring KG"

    def test_all_schema_fields_present(self) -> None:
        adapter = GuhringAdapter()
        records = adapter.parse_json_string(_minimal_json([_make_record()]))
        for field in SCHEMA_FIELDS:
            assert field in records[0], f"Missing schema field: {field}"

    def test_cutting_data_status_always_not_imported(self) -> None:
        adapter = GuhringAdapter()
        records = adapter.parse_json_string(_minimal_json([_make_record()]))
        assert records[0]["cutting_data_status"] == "not_imported"

    def test_verification_status_is_valid(self) -> None:
        from tools.tooling_adapters.base_adapter import VALID_VERIFICATION_STATUSES
        adapter = GuhringAdapter()
        records = adapter.parse_json_string(_minimal_json([_make_record()]))
        assert records[0]["verification_status"] in VALID_VERIFICATION_STATUSES

    def test_verification_status_default_value(self) -> None:
        adapter = GuhringAdapter()
        records = adapter.parse_json_string(_minimal_json([_make_record()]))
        assert records[0]["verification_status"] == "sample_family_level_not_catalog_verified"

    def test_dimensions_always_empty_dict(self) -> None:
        adapter = GuhringAdapter()
        records = adapter.parse_json_string(_minimal_json([_make_record()]))
        assert records[0]["dimensions"] == {}

    def test_source_label_preserved(self) -> None:
        adapter = GuhringAdapter()
        records = adapter.parse_json_string(_minimal_json([_make_record()]))
        assert records[0]["source_label"] == "Test Label"

    def test_source_url_preserved(self) -> None:
        adapter = GuhringAdapter()
        records = adapter.parse_json_string(_minimal_json([_make_record()]))
        assert records[0]["source_url"] == "https://example.com"

    def test_source_page_reference_preserved(self) -> None:
        adapter = GuhringAdapter()
        records = adapter.parse_json_string(_minimal_json([_make_record()]))
        assert records[0]["source_page_reference"] == "p.D-1"

    def test_material_fit_normalized_to_iso_codes(self) -> None:
        adapter = GuhringAdapter()
        records = adapter.parse_json_string(
            _minimal_json([_make_record(material_groups=["P", "M", "Z", "K"])])
        )
        assert records[0]["material_fit"] == ["P", "M", "K"]

    def test_material_fit_is_list(self) -> None:
        adapter = GuhringAdapter()
        records = adapter.parse_json_string(_minimal_json([_make_record()]))
        assert isinstance(records[0]["material_fit"], list)

    def test_operation_fit_is_list(self) -> None:
        adapter = GuhringAdapter()
        records = adapter.parse_json_string(_minimal_json([_make_record()]))
        assert isinstance(records[0]["operation_fit"], list)

    def test_operation_fit_maps_to_snake_case(self) -> None:
        adapter = GuhringAdapter()
        records = adapter.parse_json_string(
            _minimal_json([_make_record(operations=["Drilling", "ThroughHoleDrilling"])])
        )
        assert "drilling" in records[0]["operation_fit"]
        assert "through_hole_drilling" in records[0]["operation_fit"]

    def test_tapping_operation_maps_correctly(self) -> None:
        adapter = GuhringAdapter()
        records = adapter.parse_json_string(
            _minimal_json([_make_record(operations=["Tapping", "InternalThreading"])])
        )
        assert "tapping" in records[0]["operation_fit"]
        assert "internal_threading" in records[0]["operation_fit"]

    def test_thread_milling_operations_map_correctly(self) -> None:
        adapter = GuhringAdapter()
        records = adapter.parse_json_string(
            _minimal_json([_make_record(
                operations=["ThreadMilling", "ExternalThreadMilling", "InternalThreadMilling"]
            )])
        )
        assert "thread_milling" in records[0]["operation_fit"]
        assert "external_thread_milling" in records[0]["operation_fit"]
        assert "internal_thread_milling" in records[0]["operation_fit"]

    def test_reaming_operation_maps_correctly(self) -> None:
        adapter = GuhringAdapter()
        records = adapter.parse_json_string(
            _minimal_json([_make_record(operations=["Reaming", "FinishReaming"])])
        )
        assert "reaming" in records[0]["operation_fit"]
        assert "finish_reaming" in records[0]["operation_fit"]

    def test_countersinking_operation_maps_correctly(self) -> None:
        adapter = GuhringAdapter()
        records = adapter.parse_json_string(
            _minimal_json([_make_record(operations=["Countersinking", "Chamfering"])])
        )
        assert "countersinking" in records[0]["operation_fit"]
        assert "chamfering" in records[0]["operation_fit"]

    def test_geometry_tags_is_list(self) -> None:
        adapter = GuhringAdapter()
        records = adapter.parse_json_string(_minimal_json([_make_record()]))
        assert isinstance(records[0]["geometry_tags"], list)

    def test_geometry_tags_normalized_to_snake_case(self) -> None:
        adapter = GuhringAdapter()
        records = adapter.parse_json_string(
            _minimal_json([_make_record(geometry_tags=["SolidCarbide", "ThroughCoolant", "SplitPoint"])])
        )
        assert "solidcarbide" in records[0]["geometry_tags"]
        assert "throughcoolant" in records[0]["geometry_tags"]
        assert "splitpoint" in records[0]["geometry_tags"]

    def test_holder_compatibility_is_list(self) -> None:
        adapter = GuhringAdapter()
        records = adapter.parse_json_string(_minimal_json([_make_record()]))
        assert isinstance(records[0]["holder_compatibility"], list)

    def test_coolant_through_coolant_maps_correctly(self) -> None:
        adapter = GuhringAdapter()
        records = adapter.parse_json_string(
            _minimal_json([_make_record(coolant="ThroughCoolantCapable")])
        )
        assert records[0]["coolant_capability"] == "through_coolant_capable"

    def test_coolant_external_only_maps_correctly(self) -> None:
        adapter = GuhringAdapter()
        records = adapter.parse_json_string(
            _minimal_json([_make_record(coolant="ExternalOnly")])
        )
        assert records[0]["coolant_capability"] == "external_only"

    def test_coolant_unknown_maps_to_unknown(self) -> None:
        adapter = GuhringAdapter()
        records = adapter.parse_json_string(
            _minimal_json([_make_record(coolant="Unknown")])
        )
        assert records[0]["coolant_capability"] == "unknown"

    def test_tool_category_solid_carbide_drill_maps(self) -> None:
        adapter = GuhringAdapter()
        records = adapter.parse_json_string(
            _minimal_json([_make_record(tool_type="SolidCarbideDrill")])
        )
        assert records[0]["tool_category"] == "drill"

    def test_tool_category_hss_cobalt_drill_maps(self) -> None:
        adapter = GuhringAdapter()
        records = adapter.parse_json_string(
            _minimal_json([_make_record(tool_type="HSSCobaltDrill")])
        )
        assert records[0]["tool_category"] == "drill"

    def test_tool_category_machine_tap_maps(self) -> None:
        adapter = GuhringAdapter()
        records = adapter.parse_json_string(
            _minimal_json([_make_record(tool_type="MachineTap")])
        )
        assert records[0]["tool_category"] == "tap"

    def test_tool_category_thread_mill_maps(self) -> None:
        adapter = GuhringAdapter()
        records = adapter.parse_json_string(
            _minimal_json([_make_record(tool_type="ThreadMill")])
        )
        assert records[0]["tool_category"] == "thread_mill"

    def test_tool_category_endmill_maps(self) -> None:
        adapter = GuhringAdapter()
        records = adapter.parse_json_string(
            _minimal_json([_make_record(tool_type="SolidCarbideEndmill")])
        )
        assert records[0]["tool_category"] == "endmill"

    def test_tool_category_reamer_maps(self) -> None:
        adapter = GuhringAdapter()
        records = adapter.parse_json_string(
            _minimal_json([_make_record(tool_type="Reamer")])
        )
        assert records[0]["tool_category"] == "reamer"

    def test_tool_category_countersink_maps(self) -> None:
        adapter = GuhringAdapter()
        records = adapter.parse_json_string(
            _minimal_json([_make_record(tool_type="Countersink")])
        )
        assert records[0]["tool_category"] == "countersink"

    def test_tool_category_step_drill_maps(self) -> None:
        adapter = GuhringAdapter()
        records = adapter.parse_json_string(
            _minimal_json([_make_record(tool_type="StepDrill")])
        )
        assert records[0]["tool_category"] == "step_drill"

    def test_invalid_json_returns_empty_with_error(self) -> None:
        adapter = GuhringAdapter()
        records = adapter.parse_json_string("{not valid json")
        assert records == []
        assert adapter.parse_errors

    def test_top_level_array_returns_error(self) -> None:
        adapter = GuhringAdapter()
        records = adapter.parse_json_string("[]")
        assert records == []
        assert adapter.parse_errors

    def test_missing_tool_records_key_returns_error(self) -> None:
        adapter = GuhringAdapter()
        records = adapter.parse_json_string(json.dumps({"catalog_header": {}}))
        assert records == []
        assert adapter.parse_errors

    def test_forbidden_feed_rate_key_rejects_record(self) -> None:
        adapter = GuhringAdapter()
        bad = _make_record()
        bad["feed_rate"] = 0.15
        records = adapter.parse_json_string(_minimal_json([bad]))
        assert records == []
        assert adapter.rejected_count == 1
        assert any("feed" in err.lower() for err in adapter.parse_errors)

    def test_forbidden_speed_key_rejects_record(self) -> None:
        adapter = GuhringAdapter()
        bad = _make_record()
        bad["cutting_speed"] = 120
        records = adapter.parse_json_string(_minimal_json([bad]))
        assert records == []
        assert adapter.rejected_count == 1

    def test_forbidden_rpm_key_rejects_record(self) -> None:
        adapter = GuhringAdapter()
        bad = _make_record()
        bad["rpm_min"] = 500
        records = adapter.parse_json_string(_minimal_json([bad]))
        assert records == []
        assert adapter.rejected_count == 1

    def test_clean_record_not_rejected(self) -> None:
        adapter = GuhringAdapter()
        records = adapter.parse_json_string(_minimal_json([_make_record()]))
        assert len(records) == 1
        assert adapter.rejected_count == 0

    def test_forbidden_record_does_not_block_clean_records(self) -> None:
        adapter = GuhringAdapter()
        bad = _make_record(part_number="FIXTURE-BAD")
        bad["sfm"] = 200
        clean = _make_record(part_number="FIXTURE-CLEAN")
        records = adapter.parse_json_string(_minimal_json([bad, clean]))
        assert len(records) == 1
        assert records[0]["manufacturer_part_number"] == "FIXTURE-CLEAN"
        assert adapter.rejected_count == 1

    def test_no_forbidden_keys_in_output(self) -> None:
        forbidden = {"feed", "speed", "sfm", "rpm", "ipr", "ipm", "vc", "fz"}
        adapter = GuhringAdapter()
        records = adapter.parse_json_string(_minimal_json([_make_record()]))
        for record in records:
            for key in record:
                for term in forbidden:
                    assert term not in key.lower(), f"Forbidden key '{key}' in output"

    def test_validate_output_passes_for_valid_records(self) -> None:
        adapter = GuhringAdapter()
        records = adapter.parse_json_string(_minimal_json([_make_record()]))
        errors = adapter.validate_output(records)
        assert errors == []

    def test_parse_resets_state_between_calls(self) -> None:
        adapter = GuhringAdapter()
        bad = _make_record()
        bad["sfm_val"] = 100
        adapter.parse_json_string(_minimal_json([bad]))
        assert adapter.rejected_count == 1
        adapter.parse_json_string(_minimal_json([_make_record()]))
        assert adapter.rejected_count == 0
        assert adapter.parse_errors == []

    def test_importer_validation_passes_for_valid_record(self) -> None:
        adapter = GuhringAdapter()
        records = adapter.parse_json_string(_minimal_json([_make_record()]))
        errors = validate_import_rows(records)
        assert errors == []


# ── Sample file integration tests ─────────────────────────────────────────────

class TestSampleFileIntegration:
    def test_sample_file_exists(self) -> None:
        assert SAMPLE_JSON_PATH.exists(), f"Sample not found: {SAMPLE_JSON_PATH}"

    def test_sample_parses_without_errors(self) -> None:
        adapter = GuhringAdapter()
        adapter.parse(SAMPLE_JSON_PATH)
        assert adapter.parse_errors == []

    def test_sample_produces_expected_record_count(self) -> None:
        adapter = GuhringAdapter()
        records = adapter.parse(SAMPLE_JSON_PATH)
        assert len(records) == EXPECTED_RECORD_COUNT

    def test_sample_no_rejected_records(self) -> None:
        adapter = GuhringAdapter()
        adapter.parse(SAMPLE_JSON_PATH)
        assert adapter.rejected_count == 0

    def test_sample_all_records_have_all_schema_fields(self) -> None:
        adapter = GuhringAdapter()
        records = adapter.parse(SAMPLE_JSON_PATH)
        for record in records:
            missing = [f for f in SCHEMA_FIELDS if f not in record]
            assert not missing, f"Record {record.get('manufacturer_part_number')} missing: {missing}"

    def test_sample_all_brands_are_guhring(self) -> None:
        adapter = GuhringAdapter()
        records = adapter.parse(SAMPLE_JSON_PATH)
        for record in records:
            assert record["brand"] == "Guhring KG"

    def test_sample_cutting_data_status_always_not_imported(self) -> None:
        adapter = GuhringAdapter()
        records = adapter.parse(SAMPLE_JSON_PATH)
        for record in records:
            assert record["cutting_data_status"] == "not_imported"

    def test_sample_verification_status_all_valid(self) -> None:
        from tools.tooling_adapters.base_adapter import VALID_VERIFICATION_STATUSES
        adapter = GuhringAdapter()
        records = adapter.parse(SAMPLE_JSON_PATH)
        for record in records:
            assert record["verification_status"] in VALID_VERIFICATION_STATUSES

    def test_sample_dimensions_always_empty(self) -> None:
        adapter = GuhringAdapter()
        records = adapter.parse(SAMPLE_JSON_PATH)
        for record in records:
            assert record["dimensions"] == {}

    def test_sample_source_label_present(self) -> None:
        adapter = GuhringAdapter()
        records = adapter.parse(SAMPLE_JSON_PATH)
        for record in records:
            assert record.get("source_label", "").strip()

    def test_sample_source_url_present(self) -> None:
        adapter = GuhringAdapter()
        records = adapter.parse(SAMPLE_JSON_PATH)
        for record in records:
            assert record.get("source_url", "").strip()

    def test_sample_list_fields_are_lists(self) -> None:
        list_fields = ["material_fit", "operation_fit", "geometry_tags", "holder_compatibility"]
        adapter = GuhringAdapter()
        records = adapter.parse(SAMPLE_JSON_PATH)
        for record in records:
            for field in list_fields:
                assert isinstance(record.get(field), list), (
                    f"Field '{field}' not a list in {record.get('manufacturer_part_number')}"
                )

    def test_sample_material_fit_only_iso_codes(self) -> None:
        valid_codes = {"P", "M", "K", "N", "S", "H"}
        adapter = GuhringAdapter()
        records = adapter.parse(SAMPLE_JSON_PATH)
        for record in records:
            for code in record.get("material_fit", []):
                assert code in valid_codes, (
                    f"Non-ISO code '{code}' in {record.get('manufacturer_part_number')}"
                )

    def test_sample_no_forbidden_keys_in_output(self) -> None:
        forbidden = {"feed", "speed", "sfm", "rpm", "ipr", "ipm", "vc", "fz"}
        adapter = GuhringAdapter()
        records = adapter.parse(SAMPLE_JSON_PATH)
        for record in records:
            for key in record:
                for term in forbidden:
                    assert term not in key.lower(), (
                        f"Forbidden key '{key}' in {record.get('manufacturer_part_number')}"
                    )

    def test_sample_covers_expected_tool_categories(self) -> None:
        expected_categories = {"drill", "tap", "thread_mill", "endmill", "reamer", "countersink", "step_drill"}
        adapter = GuhringAdapter()
        records = adapter.parse(SAMPLE_JSON_PATH)
        found_categories = {r["tool_category"] for r in records}
        assert expected_categories.issubset(found_categories), (
            f"Missing categories: {expected_categories - found_categories}"
        )

    def test_sample_drill_records_present(self) -> None:
        adapter = GuhringAdapter()
        records = adapter.parse(SAMPLE_JSON_PATH)
        drills = [r for r in records if r["tool_category"] == "drill"]
        assert len(drills) >= 2

    def test_sample_passes_validate_adapter_output(self) -> None:
        adapter = GuhringAdapter()
        records = adapter.parse(SAMPLE_JSON_PATH)
        errors = adapter.validate_output(records)
        assert errors == [], f"Validation errors: {errors}"

    def test_sample_passes_importer_validation(self) -> None:
        adapter = GuhringAdapter()
        records = adapter.parse(SAMPLE_JSON_PATH)
        errors = validate_import_rows(records)
        assert errors == [], f"Importer errors: {errors}"

    def test_parse_guhring_file_convenience_function(self) -> None:
        result = parse_guhring_file(SAMPLE_JSON_PATH)
        assert result["record_count"] == EXPECTED_RECORD_COUNT
        assert result["rejected_count"] == 0
        assert result["parse_errors"] == []
        assert result["validation_errors"] == []

    def test_sample_notes_contain_fixture_marker(self) -> None:
        adapter = GuhringAdapter()
        records = adapter.parse(SAMPLE_JSON_PATH)
        for record in records:
            notes = record.get("notes", "").lower()
            assert "fixture" in notes or "synthetic" in notes, (
                f"Record {record.get('manufacturer_part_number')} notes: '{notes}'"
            )
