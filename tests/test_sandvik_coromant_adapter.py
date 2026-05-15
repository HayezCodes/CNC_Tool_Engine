"""Unit tests for the Sandvik Coromant structured JSON adapter."""
from __future__ import annotations
import json
from pathlib import Path
import pytest
from tools.tooling_adapters.sandvik_coromant_adapter import SandvikCoromantAdapter, parse_sandvik_coromant_file
from tools.import_tooling_records import validate_import_rows
from grade_engine.tooling_search import SCHEMA_FIELDS

SAMPLE_JSON_PATH = (
    Path(__file__).resolve().parent.parent
    / "tools" / "tooling_adapters" / "samples" / "sample_sandvik_coromant_structured.json"
)
EXPECTED_RECORD_COUNT = 10
BRAND = "Sandvik Coromant"
FORBIDDEN = {"feed", "speed", "sfm", "rpm", "ipr", "ipm", "vc", "fz"}


def _minimal_json(tool_records=None):
    return json.dumps({
        "catalog_header": {"manufacturer": BRAND, "catalog_label": "Test", "catalog_url": "https://example.com"},
        "tool_records": tool_records if tool_records is not None else [],
    })


def _make_record(**overrides):
    base = {
        "part_number": "FIXTURE-SC-TEST-001", "tool_type": "SolidCarbideDrill",
        "series": "CoroDrill 460", "family_name": "Test drill", "designation": "R460.A-12",
        "grade": "GC4325", "chipbreaker": "", "coating": "TiAlN",
        "material_groups": ["P", "M"], "operations": ["Drilling"],
        "geometry_tags": ["solid_carbide"], "holder_compatibility": "ER collet",
        "coolant": "ThroughCoolantCapable", "source_page": "p.1",
        "notes": "Synthetic fixture for testing.",
    }
    base.update(overrides)
    return base


class TestSandvikCoromantAdapterInline:
    def test_empty_records_returns_empty(self):
        a = SandvikCoromantAdapter()
        assert a.parse_json_string(_minimal_json([])) == []

    def test_single_valid_record_parses(self):
        a = SandvikCoromantAdapter()
        records = a.parse_json_string(_minimal_json([_make_record()]))
        assert len(records) == 1 and not a.parse_errors

    def test_brand_from_header(self):
        a = SandvikCoromantAdapter()
        records = a.parse_json_string(_minimal_json([_make_record()]))
        assert records[0]["brand"] == BRAND

    def test_brand_falls_back_to_constant(self):
        data = {"catalog_header": {"manufacturer": "", "catalog_label": "L", "catalog_url": "U"}, "tool_records": [_make_record()]}
        a = SandvikCoromantAdapter()
        records = a.parse_json_string(json.dumps(data))
        assert records[0]["brand"] == BRAND

    def test_all_schema_fields_present(self):
        a = SandvikCoromantAdapter()
        records = a.parse_json_string(_minimal_json([_make_record()]))
        for f in SCHEMA_FIELDS:
            assert f in records[0], f"Missing: {f}"

    def test_cutting_data_status_not_imported(self):
        a = SandvikCoromantAdapter()
        records = a.parse_json_string(_minimal_json([_make_record()]))
        assert records[0]["cutting_data_status"] == "not_imported"

    def test_verification_status_valid(self):
        from tools.tooling_adapters.base_adapter import VALID_VERIFICATION_STATUSES
        a = SandvikCoromantAdapter()
        records = a.parse_json_string(_minimal_json([_make_record()]))
        assert records[0]["verification_status"] in VALID_VERIFICATION_STATUSES

    def test_dimensions_always_empty(self):
        a = SandvikCoromantAdapter()
        records = a.parse_json_string(_minimal_json([_make_record()]))
        assert records[0]["dimensions"] == {}

    def test_source_label_preserved(self):
        a = SandvikCoromantAdapter()
        records = a.parse_json_string(_minimal_json([_make_record()]))
        assert records[0]["source_label"] == "Test"

    def test_material_fit_iso_only(self):
        a = SandvikCoromantAdapter()
        records = a.parse_json_string(_minimal_json([_make_record(material_groups=["P", "Z", "K"])]))
        assert records[0]["material_fit"] == ["P", "K"]

    def test_operation_fit_drilling_maps(self):
        a = SandvikCoromantAdapter()
        records = a.parse_json_string(_minimal_json([_make_record(operations=["Drilling", "ThroughHoleDrilling"])]))
        assert "drilling" in records[0]["operation_fit"]
        assert "through_hole_drilling" in records[0]["operation_fit"]

    def test_tool_category_solid_carbide_drill(self):
        a = SandvikCoromantAdapter()
        records = a.parse_json_string(_minimal_json([_make_record(tool_type="SolidCarbideDrill")]))
        assert records[0]["tool_category"] == "drill"

    def test_tool_category_turning_insert(self):
        a = SandvikCoromantAdapter()
        records = a.parse_json_string(_minimal_json([_make_record(tool_type="TurningInsert")]))
        assert records[0]["tool_category"] == "turning_insert"

    def test_tool_category_milling_insert(self):
        a = SandvikCoromantAdapter()
        records = a.parse_json_string(_minimal_json([_make_record(tool_type="MillingInsert")]))
        assert records[0]["tool_category"] == "milling_insert"

    def test_tool_category_high_feed_insert(self):
        a = SandvikCoromantAdapter()
        records = a.parse_json_string(_minimal_json([_make_record(tool_type="HighFeedMillingInsert")]))
        assert records[0]["tool_category"] == "high_feed_insert"

    def test_tool_category_indexable_drill(self):
        a = SandvikCoromantAdapter()
        records = a.parse_json_string(_minimal_json([_make_record(tool_type="IndexableDrill")]))
        assert records[0]["tool_category"] == "indexable_drill"

    def test_tool_category_endmill(self):
        a = SandvikCoromantAdapter()
        records = a.parse_json_string(_minimal_json([_make_record(tool_type="SolidCarbideEndmill")]))
        assert records[0]["tool_category"] == "endmill"

    def test_tool_category_grooving_insert(self):
        a = SandvikCoromantAdapter()
        records = a.parse_json_string(_minimal_json([_make_record(tool_type="GroovingInsert")]))
        assert records[0]["tool_category"] == "grooving_insert"

    def test_tool_category_threading_insert(self):
        a = SandvikCoromantAdapter()
        records = a.parse_json_string(_minimal_json([_make_record(tool_type="ThreadingInsert")]))
        assert records[0]["tool_category"] == "threading_insert"

    def test_tool_category_boring_bar(self):
        a = SandvikCoromantAdapter()
        records = a.parse_json_string(_minimal_json([_make_record(tool_type="BoringBar")]))
        assert records[0]["tool_category"] == "boring_bar"

    def test_forbidden_feed_key_rejects(self):
        a = SandvikCoromantAdapter()
        bad = _make_record(); bad["feed_rate"] = 0.2
        records = a.parse_json_string(_minimal_json([bad]))
        assert records == [] and a.rejected_count == 1

    def test_forbidden_speed_key_rejects(self):
        a = SandvikCoromantAdapter()
        bad = _make_record(); bad["cutting_speed"] = 300
        records = a.parse_json_string(_minimal_json([bad]))
        assert records == [] and a.rejected_count == 1

    def test_no_forbidden_keys_in_output(self):
        a = SandvikCoromantAdapter()
        records = a.parse_json_string(_minimal_json([_make_record()]))
        for r in records:
            for k in r:
                for t in FORBIDDEN:
                    assert t not in k.lower()

    def test_clean_record_not_rejected(self):
        a = SandvikCoromantAdapter()
        records = a.parse_json_string(_minimal_json([_make_record()]))
        assert len(records) == 1 and a.rejected_count == 0

    def test_invalid_json_returns_error(self):
        a = SandvikCoromantAdapter()
        assert a.parse_json_string("{bad") == [] and a.parse_errors

    def test_validate_output_passes(self):
        a = SandvikCoromantAdapter()
        records = a.parse_json_string(_minimal_json([_make_record()]))
        assert a.validate_output(records) == []

    def test_importer_validation_passes(self):
        a = SandvikCoromantAdapter()
        records = a.parse_json_string(_minimal_json([_make_record()]))
        assert validate_import_rows(records) == []


class TestSandvikCoromantSampleFile:
    def test_sample_exists(self):
        assert SAMPLE_JSON_PATH.exists()

    def test_sample_parses_no_errors(self):
        a = SandvikCoromantAdapter()
        a.parse(SAMPLE_JSON_PATH)
        assert a.parse_errors == []

    def test_sample_expected_count(self):
        a = SandvikCoromantAdapter()
        assert len(a.parse(SAMPLE_JSON_PATH)) == EXPECTED_RECORD_COUNT

    def test_sample_no_rejected(self):
        a = SandvikCoromantAdapter()
        a.parse(SAMPLE_JSON_PATH)
        assert a.rejected_count == 0

    def test_sample_all_schema_fields(self):
        a = SandvikCoromantAdapter()
        for r in a.parse(SAMPLE_JSON_PATH):
            missing = [f for f in SCHEMA_FIELDS if f not in r]
            assert not missing, f"{r.get('manufacturer_part_number')} missing: {missing}"

    def test_sample_all_brands_correct(self):
        a = SandvikCoromantAdapter()
        for r in a.parse(SAMPLE_JSON_PATH):
            assert r["brand"] == BRAND

    def test_sample_cutting_data_not_imported(self):
        a = SandvikCoromantAdapter()
        for r in a.parse(SAMPLE_JSON_PATH):
            assert r["cutting_data_status"] == "not_imported"

    def test_sample_dimensions_empty(self):
        a = SandvikCoromantAdapter()
        for r in a.parse(SAMPLE_JSON_PATH):
            assert r["dimensions"] == {}

    def test_sample_no_forbidden_keys(self):
        a = SandvikCoromantAdapter()
        for r in a.parse(SAMPLE_JSON_PATH):
            for k in r:
                for t in FORBIDDEN:
                    assert t not in k.lower()

    def test_sample_covers_expected_categories(self):
        expected = {"turning_insert", "milling_insert", "high_feed_insert", "drill",
                    "indexable_drill", "endmill", "grooving_insert", "threading_insert", "boring_bar"}
        a = SandvikCoromantAdapter()
        found = {r["tool_category"] for r in a.parse(SAMPLE_JSON_PATH)}
        assert expected.issubset(found), f"Missing: {expected - found}"

    def test_sample_passes_validate_output(self):
        a = SandvikCoromantAdapter()
        records = a.parse(SAMPLE_JSON_PATH)
        assert a.validate_output(records) == []

    def test_sample_passes_importer_validation(self):
        a = SandvikCoromantAdapter()
        records = a.parse(SAMPLE_JSON_PATH)
        assert validate_import_rows(records) == []

    def test_convenience_function(self):
        result = parse_sandvik_coromant_file(SAMPLE_JSON_PATH)
        assert result["record_count"] == EXPECTED_RECORD_COUNT
        assert result["rejected_count"] == 0
        assert result["parse_errors"] == []
        assert result["validation_errors"] == []

    def test_sample_notes_contain_fixture_marker(self):
        a = SandvikCoromantAdapter()
        for r in a.parse(SAMPLE_JSON_PATH):
            assert "fixture" in r.get("notes", "").lower() or "synthetic" in r.get("notes", "").lower()
