"""Integration tests: Sumitomo Electric adapter → import → audit → review → search."""
from __future__ import annotations
import json
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_ADAPTER_OUTPUT = _REPO / "tools" / "tooling_adapters" / "output" / "sumitomo_electric_sample_records.json"
_IMPORTED = _REPO / "tool_data" / "tooling_search" / "records" / "sumitomo_electric_imported_tools.json"
_REVIEWED = _REPO / "tool_data" / "tooling_search" / "records" / "reviewed" / "sumitomo_electric_reviewed_tooling_records.json"

BRAND = "Sumitomo Electric"
FORBIDDEN = {"feed", "speed", "sfm", "rpm", "ipr", "ipm", "vc", "fz"}
EXPECTED_MPNS = {
    "FIXTURE-SMT-TI-001", "FIXTURE-SMT-TI-002", "FIXTURE-SMT-MI-003", "FIXTURE-SMT-HFI-004",
    "FIXTURE-SMT-ID-005", "FIXTURE-SMT-SCE-006", "FIXTURE-SMT-GI-007", "FIXTURE-SMT-THI-008",
}


def _load(p): return json.loads(p.read_text(encoding="utf-8"))
def _no_forbidden(records, stage):
    for r in records:
        for k in r:
            for t in FORBIDDEN: assert t not in k.lower(), f"Forbidden '{k}' at {stage}"


class TestAdapterOutput:
    def test_file_exists(self): assert _ADAPTER_OUTPUT.exists()
    def test_is_list_of_8(self): assert len(_load(_ADAPTER_OUTPUT)) == 8
    def test_passes_import_validation(self):
        from tools.import_tooling_records import validate_import_rows
        assert validate_import_rows(_load(_ADAPTER_OUTPUT)) == []
    def test_no_forbidden_keys(self): _no_forbidden(_load(_ADAPTER_OUTPUT), "adapter_output")
    def test_all_brands_correct(self):
        for r in _load(_ADAPTER_OUTPUT): assert r["brand"] == BRAND
    def test_cutting_data_status(self):
        for r in _load(_ADAPTER_OUTPUT): assert r["cutting_data_status"] == "not_imported"


class TestImportedRecords:
    def test_file_exists(self): assert _IMPORTED.exists()
    def test_count_8(self): assert len(_load(_IMPORTED)) == 8
    def test_mpns_match(self):
        assert {r["manufacturer_part_number"] for r in _load(_IMPORTED)} == EXPECTED_MPNS
    def test_audit_zero_issues(self):
        from tools.audit_tooling_search_records import audit_record
        for i, r in enumerate(_load(_IMPORTED)):
            assert audit_record(r, i, _IMPORTED.name) == []
    def test_no_forbidden_keys(self): _no_forbidden(_load(_IMPORTED), "imported")
    def test_list_fields_are_lists(self):
        for r in _load(_IMPORTED):
            for f in ("material_fit", "operation_fit", "geometry_tags", "holder_compatibility"):
                assert isinstance(r.get(f), list)
    def test_mpns_have_fixture_prefix(self):
        for r in _load(_IMPORTED): assert r["manufacturer_part_number"].startswith("FIXTURE-")
    def test_covers_expected_categories(self):
        expected = {"turning_insert", "milling_insert", "high_feed_insert", "indexable_drill",
                    "endmill", "grooving_insert", "threading_insert"}
        found = {r["tool_category"] for r in _load(_IMPORTED)}
        assert expected.issubset(found)


class TestReviewedRecords:
    def test_file_exists(self): assert _REVIEWED.exists()
    def test_count_8(self): assert len(_load(_REVIEWED)) == 8
    def test_mpns_match(self):
        assert {r["manufacturer_part_number"] for r in _load(_REVIEWED)} == EXPECTED_MPNS
    def test_review_status(self):
        for r in _load(_REVIEWED): assert r["verification_status"] == "reviewed_family_level_candidate"
    def test_cutting_data_unchanged(self):
        for r in _load(_REVIEWED): assert r["cutting_data_status"] == "not_imported"
    def test_reviewer_set(self):
        for r in _load(_REVIEWED): assert r.get("reviewer") == "Joshua Hayes"
    def test_no_forbidden_keys(self): _no_forbidden(_load(_REVIEWED), "reviewed")


class TestSearchable:
    def test_brand_in_index(self):
        from grade_engine.tooling_search import load_tooling_records
        assert BRAND in {r["brand"] for r in load_tooling_records()}

    def test_8_records_in_index(self):
        from grade_engine.tooling_search import load_tooling_records
        fixture_records = [r for r in load_tooling_records()
                           if r["brand"] == BRAND and r["manufacturer_part_number"].startswith("FIXTURE-")]
        assert len(fixture_records) == 8

    def test_search_by_sumitomo(self):
        from grade_engine.tooling_search import search_tooling_records
        results = search_tooling_records("Sumitomo")
        assert results and all(r["brand"] == BRAND for r in results)

    def test_filter_by_brand(self):
        from grade_engine.tooling_search import load_tooling_records, filter_tooling_records
        results = filter_tooling_records(load_tooling_records(), {"brand": "sumitomo"})
        assert len(results) >= 8

    def test_suggest_turning_candidates(self):
        from grade_engine.tooling_search import suggest_tool_candidates
        results = suggest_tool_candidates("external_turning", "P", tool_category="turning_insert", limit=20)
        assert any(r["brand"] == BRAND for r in results)

    def test_cutting_data_in_index(self):
        from grade_engine.tooling_search import load_tooling_records
        for r in [x for x in load_tooling_records() if x["brand"] == BRAND]:
            assert r["cutting_data_status"] == "not_imported"


class TestNoFeedsOrSpeeds:
    def test_adapter_output(self): _no_forbidden(_load(_ADAPTER_OUTPUT), "adapter_output")
    def test_imported(self): _no_forbidden(_load(_IMPORTED), "imported")
    def test_reviewed(self): _no_forbidden(_load(_REVIEWED), "reviewed")
