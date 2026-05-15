"""Unit tests for the Helical Solutions structured JSON adapter."""
from __future__ import annotations
import json
from pathlib import Path
from tools.tooling_adapters.helical_solutions_adapter import HelicalSolutionsAdapter, parse_helical_solutions_file
from tools.import_tooling_records import validate_import_rows
from grade_engine.tooling_search import SCHEMA_FIELDS

SAMPLE_JSON_PATH = (
    Path(__file__).resolve().parent.parent
    / "tools" / "tooling_adapters" / "samples" / "sample_helical_solutions_structured.json"
)
EXPECTED_RECORD_COUNT = 8
BRAND = "Helical Solutions"
FORBIDDEN = {"feed", "speed", "sfm", "rpm", "ipr", "ipm", "vc", "fz"}


def _minimal_json(tool_records=None):
    return json.dumps({
        "catalog_header": {"manufacturer": BRAND, "catalog_label": "Test", "catalog_url": "https://example.com"},
        "tool_records": tool_records if tool_records is not None else [],
    })


def _make_record(**overrides):
    base = {
        "part_number": "FIXTURE-HEL-TEST-001", "tool_type": "SolidCarbideEndmill",
        "series": "HEV-5", "family_name": "Test endmill", "designation": "82740",
        "grade": "Carbide", "chipbreaker": "", "coating": "AlTiN",
        "material_groups": ["P", "M"], "operations": ["GeneralMilling"],
        "geometry_tags": ["five_flute"], "holder_compatibility": "ER collet",
        "coolant": "ExternalOnly", "source_page": "p.1",
        "notes": "Synthetic fixture for testing.",
    }
    base.update(overrides)
    return base


class TestHelicalSolutionsAdapterInline:
    def test_empty_returns_empty(self):
        assert HelicalSolutionsAdapter().parse_json_string(_minimal_json([])) == []

    def test_single_record_parses(self):
        assert len(HelicalSolutionsAdapter().parse_json_string(_minimal_json([_make_record()]))) == 1

    def test_brand_from_header(self):
        records = HelicalSolutionsAdapter().parse_json_string(_minimal_json([_make_record()]))
        assert records[0]["brand"] == BRAND

    def test_all_schema_fields(self):
        records = HelicalSolutionsAdapter().parse_json_string(_minimal_json([_make_record()]))
        for f in SCHEMA_FIELDS: assert f in records[0]

    def test_cutting_data_not_imported(self):
        records = HelicalSolutionsAdapter().parse_json_string(_minimal_json([_make_record()]))
        assert records[0]["cutting_data_status"] == "not_imported"

    def test_dimensions_empty(self):
        records = HelicalSolutionsAdapter().parse_json_string(_minimal_json([_make_record()]))
        assert records[0]["dimensions"] == {}

    def test_material_iso_only(self):
        records = HelicalSolutionsAdapter().parse_json_string(_minimal_json([_make_record(material_groups=["P", "Z", "N"])]))
        assert records[0]["material_fit"] == ["P", "N"]

    def test_tool_category_endmill(self):
        records = HelicalSolutionsAdapter().parse_json_string(_minimal_json([_make_record(tool_type="SolidCarbideEndmill")]))
        assert records[0]["tool_category"] == "endmill"

    def test_tool_category_drill(self):
        records = HelicalSolutionsAdapter().parse_json_string(_minimal_json([_make_record(tool_type="SolidCarbideDrill")]))
        assert records[0]["tool_category"] == "drill"

    def test_tool_category_thread_mill(self):
        records = HelicalSolutionsAdapter().parse_json_string(_minimal_json([_make_record(tool_type="ThreadMill")]))
        assert records[0]["tool_category"] == "thread_mill"

    def test_forbidden_feed_key_rejects(self):
        a = HelicalSolutionsAdapter(); bad = _make_record(); bad["feed_rate"] = 0.2
        assert a.parse_json_string(_minimal_json([bad])) == [] and a.rejected_count == 1

    def test_no_forbidden_keys_in_output(self):
        for r in HelicalSolutionsAdapter().parse_json_string(_minimal_json([_make_record()])):
            for k in r:
                for t in FORBIDDEN: assert t not in k.lower()

    def test_validate_output_passes(self):
        a = HelicalSolutionsAdapter()
        records = a.parse_json_string(_minimal_json([_make_record()]))
        assert a.validate_output(records) == []

    def test_importer_validation_passes(self):
        records = HelicalSolutionsAdapter().parse_json_string(_minimal_json([_make_record()]))
        assert validate_import_rows(records) == []


class TestHelicalSolutionsSampleFile:
    def test_sample_exists(self): assert SAMPLE_JSON_PATH.exists()

    def test_sample_parses_no_errors(self):
        a = HelicalSolutionsAdapter(); a.parse(SAMPLE_JSON_PATH)
        assert a.parse_errors == []

    def test_sample_expected_count(self):
        assert len(HelicalSolutionsAdapter().parse(SAMPLE_JSON_PATH)) == EXPECTED_RECORD_COUNT

    def test_sample_no_rejected(self):
        a = HelicalSolutionsAdapter(); a.parse(SAMPLE_JSON_PATH)
        assert a.rejected_count == 0

    def test_sample_all_schema_fields(self):
        for r in HelicalSolutionsAdapter().parse(SAMPLE_JSON_PATH):
            assert all(f in r for f in SCHEMA_FIELDS)

    def test_sample_all_brands_correct(self):
        for r in HelicalSolutionsAdapter().parse(SAMPLE_JSON_PATH): assert r["brand"] == BRAND

    def test_sample_cutting_data_not_imported(self):
        for r in HelicalSolutionsAdapter().parse(SAMPLE_JSON_PATH):
            assert r["cutting_data_status"] == "not_imported"

    def test_sample_no_forbidden_keys(self):
        for r in HelicalSolutionsAdapter().parse(SAMPLE_JSON_PATH):
            for k in r:
                for t in FORBIDDEN: assert t not in k.lower()

    def test_sample_covers_expected_categories(self):
        expected = {"endmill", "drill", "thread_mill"}
        found = {r["tool_category"] for r in HelicalSolutionsAdapter().parse(SAMPLE_JSON_PATH)}
        assert expected.issubset(found), f"Missing: {expected - found}"

    def test_convenience_function(self):
        result = parse_helical_solutions_file(SAMPLE_JSON_PATH)
        assert result["record_count"] == EXPECTED_RECORD_COUNT
        assert result["rejected_count"] == 0

    def test_sample_notes_contain_fixture_marker(self):
        for r in HelicalSolutionsAdapter().parse(SAMPLE_JSON_PATH):
            assert "fixture" in r.get("notes", "").lower() or "synthetic" in r.get("notes", "").lower()
