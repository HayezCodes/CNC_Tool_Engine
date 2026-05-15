"""Unit tests for the Kennametal structured JSON adapter."""
from __future__ import annotations
import json
from pathlib import Path
from tools.tooling_adapters.kennametal_adapter import KennametalAdapter, parse_kennametal_file
from tools.import_tooling_records import validate_import_rows
from grade_engine.tooling_search import SCHEMA_FIELDS

SAMPLE_JSON_PATH = (
    Path(__file__).resolve().parent.parent
    / "tools" / "tooling_adapters" / "samples" / "sample_kennametal_structured.json"
)
EXPECTED_RECORD_COUNT = 9
BRAND = "Kennametal"
FORBIDDEN = {"feed", "speed", "sfm", "rpm", "ipr", "ipm", "vc", "fz"}


def _minimal_json(tool_records=None):
    return json.dumps({
        "catalog_header": {"manufacturer": BRAND, "catalog_label": "Test", "catalog_url": "https://example.com"},
        "tool_records": tool_records if tool_records is not None else [],
    })


def _make_record(**overrides):
    base = {
        "part_number": "FIXTURE-KMT-TEST-001", "tool_type": "TurningInsert",
        "series": "Beyond KC5010", "family_name": "Test insert", "designation": "CNMG 431",
        "grade": "KC5010", "chipbreaker": "MP", "coating": "Beyond PVD",
        "material_groups": ["P", "M"], "operations": ["ExternalTurning"],
        "geometry_tags": ["negative_rake"], "holder_compatibility": "PCLNR",
        "coolant": "VerifyByCatalog", "source_page": "p.1",
        "notes": "Synthetic fixture for testing.",
    }
    base.update(overrides)
    return base


class TestKennametalAdapterInline:
    def test_empty_returns_empty(self):
        assert KennametalAdapter().parse_json_string(_minimal_json([])) == []

    def test_single_record_parses(self):
        a = KennametalAdapter()
        assert len(a.parse_json_string(_minimal_json([_make_record()]))) == 1

    def test_brand_from_header(self):
        a = KennametalAdapter()
        records = a.parse_json_string(_minimal_json([_make_record()]))
        assert records[0]["brand"] == BRAND

    def test_all_schema_fields(self):
        a = KennametalAdapter()
        records = a.parse_json_string(_minimal_json([_make_record()]))
        for f in SCHEMA_FIELDS: assert f in records[0]

    def test_cutting_data_not_imported(self):
        a = KennametalAdapter()
        records = a.parse_json_string(_minimal_json([_make_record()]))
        assert records[0]["cutting_data_status"] == "not_imported"

    def test_dimensions_empty(self):
        a = KennametalAdapter()
        records = a.parse_json_string(_minimal_json([_make_record()]))
        assert records[0]["dimensions"] == {}

    def test_material_iso_only(self):
        a = KennametalAdapter()
        records = a.parse_json_string(_minimal_json([_make_record(material_groups=["P", "Z"])]))
        assert records[0]["material_fit"] == ["P"]

    def test_tool_category_turning_insert(self):
        a = KennametalAdapter()
        records = a.parse_json_string(_minimal_json([_make_record(tool_type="TurningInsert")]))
        assert records[0]["tool_category"] == "turning_insert"

    def test_tool_category_high_feed_insert(self):
        a = KennametalAdapter()
        records = a.parse_json_string(_minimal_json([_make_record(tool_type="HighFeedMillingInsert")]))
        assert records[0]["tool_category"] == "high_feed_insert"

    def test_tool_category_drill(self):
        a = KennametalAdapter()
        records = a.parse_json_string(_minimal_json([_make_record(tool_type="SolidCarbideDrill")]))
        assert records[0]["tool_category"] == "drill"

    def test_tool_category_endmill(self):
        a = KennametalAdapter()
        records = a.parse_json_string(_minimal_json([_make_record(tool_type="SolidCarbideEndmill")]))
        assert records[0]["tool_category"] == "endmill"

    def test_tool_category_indexable_drill(self):
        a = KennametalAdapter()
        records = a.parse_json_string(_minimal_json([_make_record(tool_type="IndexableDrill")]))
        assert records[0]["tool_category"] == "indexable_drill"

    def test_forbidden_feed_key_rejects(self):
        a = KennametalAdapter(); bad = _make_record(); bad["feed_rate"] = 0.2
        assert a.parse_json_string(_minimal_json([bad])) == [] and a.rejected_count == 1

    def test_no_forbidden_keys_in_output(self):
        a = KennametalAdapter()
        for r in a.parse_json_string(_minimal_json([_make_record()])):
            for k in r:
                for t in FORBIDDEN: assert t not in k.lower()

    def test_validate_output_passes(self):
        a = KennametalAdapter()
        records = a.parse_json_string(_minimal_json([_make_record()]))
        assert a.validate_output(records) == []

    def test_importer_validation_passes(self):
        a = KennametalAdapter()
        records = a.parse_json_string(_minimal_json([_make_record()]))
        assert validate_import_rows(records) == []


class TestKennametalSampleFile:
    def test_sample_exists(self): assert SAMPLE_JSON_PATH.exists()

    def test_sample_parses_no_errors(self):
        a = KennametalAdapter(); a.parse(SAMPLE_JSON_PATH)
        assert a.parse_errors == []

    def test_sample_expected_count(self):
        assert len(KennametalAdapter().parse(SAMPLE_JSON_PATH)) == EXPECTED_RECORD_COUNT

    def test_sample_no_rejected(self):
        a = KennametalAdapter(); a.parse(SAMPLE_JSON_PATH)
        assert a.rejected_count == 0

    def test_sample_all_schema_fields(self):
        a = KennametalAdapter()
        for r in a.parse(SAMPLE_JSON_PATH):
            assert all(f in r for f in SCHEMA_FIELDS)

    def test_sample_all_brands_correct(self):
        for r in KennametalAdapter().parse(SAMPLE_JSON_PATH): assert r["brand"] == BRAND

    def test_sample_cutting_data_not_imported(self):
        for r in KennametalAdapter().parse(SAMPLE_JSON_PATH):
            assert r["cutting_data_status"] == "not_imported"

    def test_sample_no_forbidden_keys(self):
        for r in KennametalAdapter().parse(SAMPLE_JSON_PATH):
            for k in r:
                for t in FORBIDDEN: assert t not in k.lower()

    def test_sample_covers_expected_categories(self):
        expected = {"turning_insert", "milling_insert", "high_feed_insert", "drill",
                    "indexable_drill", "endmill", "grooving_insert", "threading_insert"}
        found = {r["tool_category"] for r in KennametalAdapter().parse(SAMPLE_JSON_PATH)}
        assert expected.issubset(found)

    def test_convenience_function(self):
        result = parse_kennametal_file(SAMPLE_JSON_PATH)
        assert result["record_count"] == EXPECTED_RECORD_COUNT
        assert result["rejected_count"] == 0

    def test_sample_notes_contain_fixture_marker(self):
        for r in KennametalAdapter().parse(SAMPLE_JSON_PATH):
            assert "fixture" in r.get("notes", "").lower() or "synthetic" in r.get("notes", "").lower()
