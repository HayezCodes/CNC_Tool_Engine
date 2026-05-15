"""Unit tests for the Seco Tools structured JSON adapter."""
from __future__ import annotations
import json
from pathlib import Path
from tools.tooling_adapters.seco_adapter import SecoToolsAdapter, parse_seco_tools_file
from tools.import_tooling_records import validate_import_rows
from grade_engine.tooling_search import SCHEMA_FIELDS

SAMPLE_JSON_PATH = (
    Path(__file__).resolve().parent.parent
    / "tools" / "tooling_adapters" / "samples" / "sample_seco_structured.json"
)
EXPECTED_RECORD_COUNT = 9
BRAND = "Seco Tools"
FORBIDDEN = {"feed", "speed", "sfm", "rpm", "ipr", "ipm", "vc", "fz"}


def _minimal_json(tool_records=None):
    return json.dumps({
        "catalog_header": {"manufacturer": BRAND, "catalog_label": "Test", "catalog_url": "https://example.com"},
        "tool_records": tool_records if tool_records is not None else [],
    })


def _make_record(**overrides):
    base = {
        "part_number": "FIXTURE-SECO-TEST-001", "tool_type": "TurningInsert",
        "series": "Duratomic TC", "family_name": "Test turning insert", "designation": "CNMG 120408",
        "grade": "TP2500", "chipbreaker": "MF4", "coating": "Duratomic CVD",
        "material_groups": ["P", "M"], "operations": ["ExternalTurning"],
        "geometry_tags": ["negative_rake"], "holder_compatibility": "PCLNR holders",
        "coolant": "VerifyByCatalog", "source_page": "p.1",
        "notes": "Synthetic fixture for testing.",
    }
    base.update(overrides)
    return base


class TestSecoAdapterInline:
    def test_empty_returns_empty(self):
        assert SecoToolsAdapter().parse_json_string(_minimal_json([])) == []

    def test_single_record_parses(self):
        a = SecoToolsAdapter()
        assert len(a.parse_json_string(_minimal_json([_make_record()]))) == 1

    def test_brand_from_header(self):
        a = SecoToolsAdapter()
        records = a.parse_json_string(_minimal_json([_make_record()]))
        assert records[0]["brand"] == BRAND

    def test_all_schema_fields(self):
        a = SecoToolsAdapter()
        records = a.parse_json_string(_minimal_json([_make_record()]))
        for f in SCHEMA_FIELDS:
            assert f in records[0]

    def test_cutting_data_not_imported(self):
        a = SecoToolsAdapter()
        records = a.parse_json_string(_minimal_json([_make_record()]))
        assert records[0]["cutting_data_status"] == "not_imported"

    def test_dimensions_empty(self):
        a = SecoToolsAdapter()
        records = a.parse_json_string(_minimal_json([_make_record()]))
        assert records[0]["dimensions"] == {}

    def test_material_fit_iso_only(self):
        a = SecoToolsAdapter()
        records = a.parse_json_string(_minimal_json([_make_record(material_groups=["P", "X", "M"])]))
        assert records[0]["material_fit"] == ["P", "M"]

    def test_tool_category_turning_insert(self):
        a = SecoToolsAdapter()
        records = a.parse_json_string(_minimal_json([_make_record(tool_type="TurningInsert")]))
        assert records[0]["tool_category"] == "turning_insert"

    def test_tool_category_high_feed_insert(self):
        a = SecoToolsAdapter()
        records = a.parse_json_string(_minimal_json([_make_record(tool_type="HighFeedMillingInsert")]))
        assert records[0]["tool_category"] == "high_feed_insert"

    def test_tool_category_drill(self):
        a = SecoToolsAdapter()
        records = a.parse_json_string(_minimal_json([_make_record(tool_type="SolidCarbideDrill")]))
        assert records[0]["tool_category"] == "drill"

    def test_tool_category_endmill(self):
        a = SecoToolsAdapter()
        records = a.parse_json_string(_minimal_json([_make_record(tool_type="SolidCarbideEndmill")]))
        assert records[0]["tool_category"] == "endmill"

    def test_tool_category_grooving_insert(self):
        a = SecoToolsAdapter()
        records = a.parse_json_string(_minimal_json([_make_record(tool_type="GroovingInsert")]))
        assert records[0]["tool_category"] == "grooving_insert"

    def test_tool_category_threading_insert(self):
        a = SecoToolsAdapter()
        records = a.parse_json_string(_minimal_json([_make_record(tool_type="ThreadingInsert")]))
        assert records[0]["tool_category"] == "threading_insert"

    def test_tool_category_boring_bar(self):
        a = SecoToolsAdapter()
        records = a.parse_json_string(_minimal_json([_make_record(tool_type="BoringBar")]))
        assert records[0]["tool_category"] == "boring_bar"

    def test_forbidden_feed_key_rejects(self):
        a = SecoToolsAdapter()
        bad = _make_record(); bad["feed_rate"] = 0.2
        assert a.parse_json_string(_minimal_json([bad])) == [] and a.rejected_count == 1

    def test_forbidden_speed_key_rejects(self):
        a = SecoToolsAdapter()
        bad = _make_record(); bad["cutting_speed"] = 300
        assert a.parse_json_string(_minimal_json([bad])) == [] and a.rejected_count == 1

    def test_no_forbidden_keys_in_output(self):
        a = SecoToolsAdapter()
        for r in a.parse_json_string(_minimal_json([_make_record()])):
            for k in r:
                for t in FORBIDDEN: assert t not in k.lower()

    def test_validate_output_passes(self):
        a = SecoToolsAdapter()
        records = a.parse_json_string(_minimal_json([_make_record()]))
        assert a.validate_output(records) == []

    def test_importer_validation_passes(self):
        a = SecoToolsAdapter()
        records = a.parse_json_string(_minimal_json([_make_record()]))
        assert validate_import_rows(records) == []


class TestSecoSampleFile:
    def test_sample_exists(self): assert SAMPLE_JSON_PATH.exists()

    def test_sample_parses_no_errors(self):
        a = SecoToolsAdapter(); a.parse(SAMPLE_JSON_PATH)
        assert a.parse_errors == []

    def test_sample_expected_count(self):
        assert len(SecoToolsAdapter().parse(SAMPLE_JSON_PATH)) == EXPECTED_RECORD_COUNT

    def test_sample_no_rejected(self):
        a = SecoToolsAdapter(); a.parse(SAMPLE_JSON_PATH)
        assert a.rejected_count == 0

    def test_sample_all_schema_fields(self):
        a = SecoToolsAdapter()
        for r in a.parse(SAMPLE_JSON_PATH):
            assert all(f in r for f in SCHEMA_FIELDS)

    def test_sample_all_brands_correct(self):
        a = SecoToolsAdapter()
        for r in a.parse(SAMPLE_JSON_PATH): assert r["brand"] == BRAND

    def test_sample_cutting_data_not_imported(self):
        a = SecoToolsAdapter()
        for r in a.parse(SAMPLE_JSON_PATH): assert r["cutting_data_status"] == "not_imported"

    def test_sample_dimensions_empty(self):
        a = SecoToolsAdapter()
        for r in a.parse(SAMPLE_JSON_PATH): assert r["dimensions"] == {}

    def test_sample_no_forbidden_keys(self):
        a = SecoToolsAdapter()
        for r in a.parse(SAMPLE_JSON_PATH):
            for k in r:
                for t in FORBIDDEN: assert t not in k.lower()

    def test_sample_covers_expected_categories(self):
        expected = {"turning_insert", "milling_insert", "high_feed_insert", "drill", "endmill",
                    "grooving_insert", "threading_insert", "boring_bar"}
        found = {r["tool_category"] for r in SecoToolsAdapter().parse(SAMPLE_JSON_PATH)}
        assert expected.issubset(found), f"Missing: {expected - found}"

    def test_convenience_function(self):
        result = parse_seco_tools_file(SAMPLE_JSON_PATH)
        assert result["record_count"] == EXPECTED_RECORD_COUNT
        assert result["rejected_count"] == 0
        assert result["parse_errors"] == []

    def test_sample_notes_contain_fixture_marker(self):
        a = SecoToolsAdapter()
        for r in a.parse(SAMPLE_JSON_PATH):
            assert "fixture" in r.get("notes", "").lower() or "synthetic" in r.get("notes", "").lower()
