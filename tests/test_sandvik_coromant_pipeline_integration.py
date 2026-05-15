"""Integration tests: Sandvik Coromant adapter → import → audit → review → search."""
from __future__ import annotations
import json
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_ADAPTER_OUTPUT = _REPO / "tools" / "tooling_adapters" / "output" / "sandvik_coromant_sample_records.json"
_IMPORTED = _REPO / "tool_data" / "tooling_search" / "records" / "sandvik_coromant_imported_tools.json"
_REVIEWED = _REPO / "tool_data" / "tooling_search" / "records" / "reviewed" / "sandvik_coromant_reviewed_tooling_records.json"

BRAND = "Sandvik Coromant"
FORBIDDEN = {"feed", "speed", "sfm", "rpm", "ipr", "ipm", "vc", "fz"}
EXPECTED_MPNS = {
    "FIXTURE-SC-TI-001", "FIXTURE-SC-TI-002", "FIXTURE-SC-MI-003", "FIXTURE-SC-HFI-004",
    "FIXTURE-SC-SCD-005", "FIXTURE-SC-ID-006", "FIXTURE-SC-SCE-007",
    "FIXTURE-SC-GI-008", "FIXTURE-SC-THI-009", "FIXTURE-SC-BB-010",
}


def _load(p): return json.loads(p.read_text(encoding="utf-8"))
def _no_forbidden(records, stage):
    for r in records:
        for k in r:
            for t in FORBIDDEN:
                assert t not in k.lower(), f"Forbidden key '{k}' at {stage}"


class TestAdapterOutput:
    def test_file_exists(self): assert _ADAPTER_OUTPUT.exists()
    def test_is_list_of_10(self): assert len(_load(_ADAPTER_OUTPUT)) == 10
    def test_passes_import_validation(self):
        from tools.import_tooling_records import validate_import_rows
        assert validate_import_rows(_load(_ADAPTER_OUTPUT)) == []
    def test_no_forbidden_keys(self): _no_forbidden(_load(_ADAPTER_OUTPUT), "adapter_output")
    def test_all_brands_correct(self):
        for r in _load(_ADAPTER_OUTPUT): assert r["brand"] == BRAND
    def test_cutting_data_status(self):
        for r in _load(_ADAPTER_OUTPUT): assert r["cutting_data_status"] == "not_imported"
    def test_dimensions_empty(self):
        for r in _load(_ADAPTER_OUTPUT): assert r["dimensions"] == {}


class TestImportedRecords:
    def test_file_exists(self): assert _IMPORTED.exists()
    def test_count_10(self): assert len(_load(_IMPORTED)) == 10
    def test_mpns_match(self):
        assert {r["manufacturer_part_number"] for r in _load(_IMPORTED)} == EXPECTED_MPNS
    def test_all_schema_fields(self):
        from grade_engine.tooling_search import SCHEMA_FIELDS
        for r in _load(_IMPORTED):
            assert all(f in r for f in SCHEMA_FIELDS)
    def test_audit_zero_issues(self):
        from tools.audit_tooling_search_records import audit_record
        for i, r in enumerate(_load(_IMPORTED)):
            assert audit_record(r, i, _IMPORTED.name) == []
    def test_cutting_data_status(self):
        for r in _load(_IMPORTED): assert r["cutting_data_status"] == "not_imported"
    def test_no_forbidden_keys(self): _no_forbidden(_load(_IMPORTED), "imported")
    def test_material_fit_iso_only(self):
        valid = {"P", "M", "K", "N", "S", "H"}
        for r in _load(_IMPORTED):
            for c in r.get("material_fit", []): assert c in valid
    def test_list_fields_are_lists(self):
        for r in _load(_IMPORTED):
            for f in ("material_fit", "operation_fit", "geometry_tags", "holder_compatibility"):
                assert isinstance(r.get(f), list)
    def test_source_url_present(self):
        for r in _load(_IMPORTED): assert r.get("source_url", "").strip()
    def test_covers_expected_categories(self):
        expected = {"turning_insert", "milling_insert", "high_feed_insert", "drill",
                    "indexable_drill", "endmill", "grooving_insert", "threading_insert", "boring_bar"}
        found = {r["tool_category"] for r in _load(_IMPORTED)}
        assert expected.issubset(found)
    def test_mpns_have_fixture_prefix(self):
        for r in _load(_IMPORTED):
            assert r["manufacturer_part_number"].startswith("FIXTURE-")


class TestReviewedRecords:
    def test_file_exists(self): assert _REVIEWED.exists()
    def test_count_10(self): assert len(_load(_REVIEWED)) == 10
    def test_mpns_match(self):
        assert {r["manufacturer_part_number"] for r in _load(_REVIEWED)} == EXPECTED_MPNS
    def test_review_status(self):
        for r in _load(_REVIEWED): assert r["verification_status"] == "reviewed_family_level_candidate"
    def test_cutting_data_unchanged(self):
        for r in _load(_REVIEWED): assert r["cutting_data_status"] == "not_imported"
    def test_reviewer_set(self):
        for r in _load(_REVIEWED): assert r.get("reviewer") == "Joshua Hayes"
    def test_review_date_set(self):
        for r in _load(_REVIEWED): assert r.get("review_date", "").strip()
    def test_review_notes_present(self):
        for r in _load(_REVIEWED):
            notes = r.get("review_notes", "").lower()
            assert "pipeline" in notes or "fixture" in notes or "not manufacturer" in notes
    def test_no_forbidden_keys(self): _no_forbidden(_load(_REVIEWED), "reviewed")
    def test_dimensions_empty(self):
        for r in _load(_REVIEWED): assert r.get("dimensions") == {}


class TestSearchable:
    def test_brand_in_load_tooling_records(self):
        from grade_engine.tooling_search import load_tooling_records
        brands = {r["brand"] for r in load_tooling_records()}
        assert BRAND in brands

    def test_10_records_in_index(self):
        from grade_engine.tooling_search import load_tooling_records
        fixture_records = [r for r in load_tooling_records()
                           if r["brand"] == BRAND and r["manufacturer_part_number"].startswith("FIXTURE-")]
        assert len(fixture_records) == 10

    def test_mpns_in_index(self):
        from grade_engine.tooling_search import load_tooling_records
        indexed = {r["manufacturer_part_number"] for r in load_tooling_records()
                   if r["brand"] == BRAND and r["manufacturer_part_number"].startswith("FIXTURE-")}
        assert indexed == EXPECTED_MPNS

    def test_search_by_sandvik(self):
        from grade_engine.tooling_search import search_tooling_records
        results = search_tooling_records("Sandvik")
        assert results and all(r["brand"] == BRAND for r in results)

    def test_filter_by_brand(self):
        from grade_engine.tooling_search import load_tooling_records, filter_tooling_records
        results = filter_tooling_records(load_tooling_records(), {"brand": "sandvik"})
        assert len(results) >= 10

    def test_filter_turning_insert(self):
        from grade_engine.tooling_search import load_tooling_records, filter_tooling_records
        results = filter_tooling_records(load_tooling_records(), {"brand": "sandvik", "tool_category": "turning_insert"})
        fixture_results = [r for r in results if r["manufacturer_part_number"].startswith("FIXTURE-")]
        assert len(fixture_results) == 2

    def test_filter_by_material_p(self):
        from grade_engine.tooling_search import load_tooling_records, filter_tooling_records
        results = filter_tooling_records(load_tooling_records(), {"brand": "sandvik", "material_group": "P"})
        assert results and all("P" in r["material_fit"] for r in results)

    def test_suggest_turning_candidates(self):
        from grade_engine.tooling_search import suggest_tool_candidates
        results = suggest_tool_candidates("external_turning", "P", tool_category="turning_insert", limit=20)
        sc = [r for r in results if r["brand"] == BRAND]
        assert sc  # at least one Sandvik turning insert candidate

    def test_total_index_size_grows(self):
        from grade_engine.tooling_search import load_tooling_records
        assert len(load_tooling_records()) >= 110  # 82 base + 28 new from batch 1

    def test_cutting_data_in_index(self):
        from grade_engine.tooling_search import load_tooling_records
        for r in [x for x in load_tooling_records() if x["brand"] == BRAND]:
            assert r["cutting_data_status"] == "not_imported"


class TestNoFeedsOrSpeeds:
    def test_adapter_output(self): _no_forbidden(_load(_ADAPTER_OUTPUT), "adapter_output")
    def test_imported(self): _no_forbidden(_load(_IMPORTED), "imported")
    def test_reviewed(self): _no_forbidden(_load(_REVIEWED), "reviewed")
    def test_index(self):
        from grade_engine.tooling_search import load_tooling_records
        _no_forbidden([r for r in load_tooling_records() if r["brand"] == BRAND], "index")
