"""Integration tests for the Iscar adapter-to-search pipeline.

Proves the full flow:
    adapter output → import → audit → review → searchable tooling records

All records tested here are synthetic fixtures, clearly marked as not manufacturer
catalog data.  No feeds, speeds, or dimensions are expected at any stage.
"""

from __future__ import annotations

import json
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_ADAPTER_OUTPUT = (
    _REPO / "tools" / "tooling_adapters" / "output" / "iscar_sample_records.json"
)
_IMPORTED_PATH = (
    _REPO / "tool_data" / "tooling_search" / "records" / "iscar_imported_tools.json"
)
_REVIEWED_PATH = (
    _REPO
    / "tool_data"
    / "tooling_search"
    / "records"
    / "reviewed"
    / "iscar_reviewed_tools.json"
)

_EXPECTED_MPN_SET = {
    "FIXTURE-ISC-TI-001",
    "FIXTURE-ISC-TI-002",
    "FIXTURE-ISC-MI-003",
    "FIXTURE-ISC-HF-004",
    "FIXTURE-ISC-IDR-005",
    "FIXTURE-ISC-GRV-006",
    "FIXTURE-ISC-THR-007",
    "FIXTURE-ISC-BB-008",
}
_EXPECTED_BRAND = "Iscar Ltd."
_FORBIDDEN_TERMS = {"feed", "speed", "sfm", "rpm", "ipr", "ipm", "vc", "fz"}


def _load(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


# ── Stage 1: Adapter output validates through importer ────────────────────────

class TestAdapterOutputImportsSuccessfully:
    def test_adapter_output_file_exists(self) -> None:
        assert _ADAPTER_OUTPUT.exists(), f"Adapter output not found: {_ADAPTER_OUTPUT}"

    def test_adapter_output_is_json_list(self) -> None:
        records = _load(_ADAPTER_OUTPUT)
        assert isinstance(records, list)
        assert len(records) == 8

    def test_adapter_output_passes_import_validation(self) -> None:
        from tools.import_tooling_records import validate_import_rows
        errors = validate_import_rows(_load(_ADAPTER_OUTPUT))
        assert errors == [], f"Import validation errors: {errors}"

    def test_adapter_output_has_no_forbidden_keys(self) -> None:
        for record in _load(_ADAPTER_OUTPUT):
            for key in record:
                for term in _FORBIDDEN_TERMS:
                    assert term not in key.lower(), (
                        f"Forbidden key '{key}' in adapter output "
                        f"{record.get('manufacturer_part_number', '?')}"
                    )

    def test_adapter_output_all_brands_are_iscar(self) -> None:
        for record in _load(_ADAPTER_OUTPUT):
            assert record["brand"] == _EXPECTED_BRAND

    def test_adapter_output_cutting_data_status(self) -> None:
        for record in _load(_ADAPTER_OUTPUT):
            assert record["cutting_data_status"] == "not_imported"

    def test_adapter_output_verification_status(self) -> None:
        for record in _load(_ADAPTER_OUTPUT):
            assert record["verification_status"] == "sample_family_level_not_catalog_verified"

    def test_adapter_output_dimensions_empty(self) -> None:
        for record in _load(_ADAPTER_OUTPUT):
            assert record["dimensions"] == {}


# ── Stage 2: Imported records exist and audit cleanly ─────────────────────────

class TestImportedRecordsAuditCleanly:
    def test_imported_file_exists(self) -> None:
        assert _IMPORTED_PATH.exists(), f"Imported records not found: {_IMPORTED_PATH}"

    def test_imported_file_is_json_list(self) -> None:
        records = _load(_IMPORTED_PATH)
        assert isinstance(records, list)
        assert len(records) == 8

    def test_imported_mpns_match_expected(self) -> None:
        mpns = {r["manufacturer_part_number"] for r in _load(_IMPORTED_PATH)}
        assert mpns == _EXPECTED_MPN_SET

    def test_imported_records_have_all_schema_fields(self) -> None:
        from grade_engine.tooling_search import SCHEMA_FIELDS
        for record in _load(_IMPORTED_PATH):
            missing = [f for f in SCHEMA_FIELDS if f not in record]
            assert not missing, (
                f"Record {record.get('manufacturer_part_number')} missing: {missing}"
            )

    def test_imported_records_audit_zero_issues(self) -> None:
        from tools.audit_tooling_search_records import audit_record
        for idx, record in enumerate(_load(_IMPORTED_PATH)):
            issues = audit_record(record, idx, _IMPORTED_PATH.name)
            assert issues == [], (
                f"Audit issues in {record.get('manufacturer_part_number')}: {issues}"
            )

    def test_imported_records_cutting_data_status(self) -> None:
        for record in _load(_IMPORTED_PATH):
            assert record["cutting_data_status"] == "not_imported"

    def test_imported_records_verification_status(self) -> None:
        for record in _load(_IMPORTED_PATH):
            assert record["verification_status"] == "sample_family_level_not_catalog_verified"

    def test_imported_records_no_forbidden_keys(self) -> None:
        for record in _load(_IMPORTED_PATH):
            for key in record:
                for term in _FORBIDDEN_TERMS:
                    assert term not in key.lower(), (
                        f"Forbidden key '{key}' in {record.get('manufacturer_part_number', '?')}"
                    )

    def test_imported_records_dimensions_empty(self) -> None:
        for record in _load(_IMPORTED_PATH):
            assert record["dimensions"] == {}

    def test_imported_records_material_fit_only_iso_codes(self) -> None:
        valid_codes = {"P", "M", "K", "N", "S", "H"}
        for record in _load(_IMPORTED_PATH):
            for code in record.get("material_fit", []):
                assert code in valid_codes, (
                    f"Non-ISO code '{code}' in {record.get('manufacturer_part_number')}"
                )

    def test_imported_records_list_fields_are_lists(self) -> None:
        list_fields = ["material_fit", "operation_fit", "geometry_tags", "holder_compatibility"]
        for record in _load(_IMPORTED_PATH):
            for field in list_fields:
                assert isinstance(record.get(field), list), (
                    f"'{field}' not a list in {record.get('manufacturer_part_number')}"
                )

    def test_imported_records_source_url_present(self) -> None:
        for record in _load(_IMPORTED_PATH):
            assert record.get("source_url", "").strip()

    def test_imported_records_source_label_present(self) -> None:
        for record in _load(_IMPORTED_PATH):
            assert record.get("source_label", "").strip()

    def test_imported_covers_all_expected_categories(self) -> None:
        expected = {
            "turning_insert", "milling_insert", "high_feed_insert",
            "indexable_drill", "grooving_insert", "threading_insert", "boring_bar",
        }
        found = {r["tool_category"] for r in _load(_IMPORTED_PATH)}
        assert expected.issubset(found), f"Missing categories: {expected - found}"

    def test_imported_high_feed_insert_category_exists(self) -> None:
        records = _load(_IMPORTED_PATH)
        hf = [r for r in records if r["tool_category"] == "high_feed_insert"]
        assert len(hf) == 1
        assert hf[0]["manufacturer_part_number"] == "FIXTURE-ISC-HF-004"

    def test_imported_boring_bar_category_exists(self) -> None:
        records = _load(_IMPORTED_PATH)
        bb = [r for r in records if r["tool_category"] == "boring_bar"]
        assert len(bb) == 1
        assert bb[0]["manufacturer_part_number"] == "FIXTURE-ISC-BB-008"


# ── Stage 3: Reviewed records correctly promoted ──────────────────────────────

class TestReviewedRecordsCorrectlyPromoted:
    def test_reviewed_file_exists(self) -> None:
        assert _REVIEWED_PATH.exists(), f"Reviewed records not found: {_REVIEWED_PATH}"

    def test_reviewed_file_is_json_list(self) -> None:
        records = _load(_REVIEWED_PATH)
        assert isinstance(records, list)
        assert len(records) == 8

    def test_reviewed_mpns_match_expected(self) -> None:
        mpns = {r["manufacturer_part_number"] for r in _load(_REVIEWED_PATH)}
        assert mpns == _EXPECTED_MPN_SET

    def test_reviewed_status_is_family_level_candidate(self) -> None:
        for record in _load(_REVIEWED_PATH):
            assert record["verification_status"] == "reviewed_family_level_candidate"

    def test_reviewed_cutting_data_status_unchanged(self) -> None:
        for record in _load(_REVIEWED_PATH):
            assert record["cutting_data_status"] == "not_imported"

    def test_reviewed_reviewer_field_set(self) -> None:
        for record in _load(_REVIEWED_PATH):
            assert record.get("reviewer") == "Joshua Hayes"

    def test_reviewed_review_date_set(self) -> None:
        for record in _load(_REVIEWED_PATH):
            assert record.get("review_date", "").strip()

    def test_reviewed_review_notes_present(self) -> None:
        for record in _load(_REVIEWED_PATH):
            notes = record.get("review_notes", "")
            assert "pipeline" in notes.lower() or "fixture" in notes.lower()

    def test_reviewed_records_no_forbidden_keys(self) -> None:
        for record in _load(_REVIEWED_PATH):
            for key in record:
                for term in _FORBIDDEN_TERMS:
                    assert term not in key.lower(), (
                        f"Forbidden key '{key}' in reviewed "
                        f"{record.get('manufacturer_part_number', '?')}"
                    )

    def test_reviewed_records_dimensions_empty(self) -> None:
        for record in _load(_REVIEWED_PATH):
            assert record.get("dimensions") == {}

    def test_reviewed_records_audit_clean(self) -> None:
        from tools.audit_tooling_search_records import audit_record, VALID_VERIFICATION_STATUSES
        assert "reviewed_family_level_candidate" in VALID_VERIFICATION_STATUSES
        for idx, record in enumerate(_load(_REVIEWED_PATH)):
            issues = audit_record(record, idx, _REVIEWED_PATH.name)
            assert issues == [], (
                f"Audit issues in reviewed {record.get('manufacturer_part_number')}: {issues}"
            )


# ── Stage 4: Iscar records searchable via tooling_search ─────────────────────

class TestIscarRecordsSearchable:
    def test_iscar_records_in_load_tooling_records(self) -> None:
        from grade_engine.tooling_search import load_tooling_records
        iscar = [r for r in load_tooling_records() if r["brand"] == _EXPECTED_BRAND]
        assert len(iscar) == 8

    def test_iscar_mpns_all_present_in_search_index(self) -> None:
        from grade_engine.tooling_search import load_tooling_records
        indexed = {r["manufacturer_part_number"] for r in load_tooling_records() if r["brand"] == _EXPECTED_BRAND}
        assert indexed == _EXPECTED_MPN_SET

    def test_search_by_iscar_brand_returns_records(self) -> None:
        from grade_engine.tooling_search import search_tooling_records
        results = search_tooling_records("Iscar")
        assert results
        assert all(r["brand"] == _EXPECTED_BRAND for r in results)

    def test_search_by_iscar_returns_all_8(self) -> None:
        from grade_engine.tooling_search import search_tooling_records
        results = search_tooling_records("Iscar Ltd")
        assert len(results) == 8

    def test_filter_by_iscar_brand(self) -> None:
        from grade_engine.tooling_search import load_tooling_records, filter_tooling_records
        results = filter_tooling_records(load_tooling_records(), {"brand": "iscar"})
        assert len(results) == 8
        assert all(r["brand"] == _EXPECTED_BRAND for r in results)

    def test_filter_iscar_turning_inserts(self) -> None:
        from grade_engine.tooling_search import load_tooling_records, filter_tooling_records
        results = filter_tooling_records(
            load_tooling_records(),
            {"brand": "iscar", "tool_category": "turning_insert"},
        )
        assert len(results) == 2
        assert all(r["tool_category"] == "turning_insert" for r in results)

    def test_filter_iscar_high_feed_insert(self) -> None:
        from grade_engine.tooling_search import load_tooling_records, filter_tooling_records
        results = filter_tooling_records(
            load_tooling_records(),
            {"brand": "iscar", "tool_category": "high_feed_insert"},
        )
        assert len(results) == 1
        assert results[0]["manufacturer_part_number"] == "FIXTURE-ISC-HF-004"

    def test_filter_iscar_boring_bar(self) -> None:
        from grade_engine.tooling_search import load_tooling_records, filter_tooling_records
        results = filter_tooling_records(
            load_tooling_records(),
            {"brand": "iscar", "tool_category": "boring_bar"},
        )
        assert len(results) == 1
        assert results[0]["manufacturer_part_number"] == "FIXTURE-ISC-BB-008"

    def test_filter_iscar_by_material_group_p(self) -> None:
        from grade_engine.tooling_search import load_tooling_records, filter_tooling_records
        results = filter_tooling_records(
            load_tooling_records(),
            {"brand": "iscar", "material_group": "P"},
        )
        assert results
        assert all("P" in r["material_fit"] for r in results)

    def test_filter_iscar_by_high_feed_milling_operation(self) -> None:
        from grade_engine.tooling_search import load_tooling_records, filter_tooling_records
        results = filter_tooling_records(
            load_tooling_records(),
            {"brand": "iscar", "operation": "high_feed_milling"},
        )
        assert results
        assert all("high_feed_milling" in r["operation_fit"] for r in results)

    def test_search_by_iscar_mpn(self) -> None:
        from grade_engine.tooling_search import search_tooling_records
        results = search_tooling_records("FIXTURE-ISC-HF-004")
        assert results
        assert results[0]["manufacturer_part_number"] == "FIXTURE-ISC-HF-004"

    def test_search_sumocham_returns_indexable_drill(self) -> None:
        from grade_engine.tooling_search import search_tooling_records
        results = search_tooling_records("SUMOCHAM")
        assert results
        assert any(r["tool_category"] == "indexable_drill" for r in results)

    def test_explain_tool_match_returns_reasons_for_iscar(self) -> None:
        from grade_engine.tooling_search import search_tooling_records, explain_tool_match
        results = search_tooling_records("Iscar")
        assert results
        reasons = explain_tool_match(results[0], "Iscar")
        assert reasons
        assert any("brand" in r.lower() or "iscar" in r.lower() for r in reasons)

    def test_iscar_records_have_required_display_fields(self) -> None:
        from grade_engine.tooling_search import load_tooling_records
        for record in [r for r in load_tooling_records() if r["brand"] == _EXPECTED_BRAND]:
            assert "brand" in record
            assert "manufacturer_part_number" in record
            assert "tool_category" in record
            assert isinstance(record.get("material_fit"), list)
            assert isinstance(record.get("operation_fit"), list)
            assert "verification_status" in record
            assert "cutting_data_status" in record

    def test_total_record_count_includes_iscar(self) -> None:
        from grade_engine.tooling_search import load_tooling_records
        all_records = load_tooling_records()
        brands = {r["brand"] for r in all_records}
        assert _EXPECTED_BRAND in brands
        assert len(all_records) >= 63


# ── Stage 5: No feeds/speeds at any stage ────────────────────────────────────

class TestNoFeedsOrSpeedsAtAnyStage:
    def _check(self, records: list[dict], stage: str) -> None:
        for record in records:
            for key in record:
                for term in _FORBIDDEN_TERMS:
                    assert term not in key.lower(), (
                        f"Forbidden key '{key}' at {stage} in "
                        f"{record.get('manufacturer_part_number', '?')}"
                    )

    def test_adapter_output_no_forbidden_keys(self) -> None:
        self._check(_load(_ADAPTER_OUTPUT), "adapter_output")

    def test_imported_no_forbidden_keys(self) -> None:
        self._check(_load(_IMPORTED_PATH), "imported")

    def test_reviewed_no_forbidden_keys(self) -> None:
        self._check(_load(_REVIEWED_PATH), "reviewed")

    def test_search_index_iscar_records_no_forbidden_keys(self) -> None:
        from grade_engine.tooling_search import load_tooling_records
        iscar = [r for r in load_tooling_records() if r["brand"] == _EXPECTED_BRAND]
        self._check(iscar, "search_index")

    def test_no_forbidden_key_patterns_in_imported_text(self) -> None:
        text = _IMPORTED_PATH.read_text(encoding="utf-8").lower()
        for pattern in ("feed_rate", "spindle_speed", "sfm_value", "rpm_recommended"):
            assert pattern not in text, f"Suspicious key pattern '{pattern}' in imported records"


# ── Stage 6: Records clearly marked as synthetic ──────────────────────────────

class TestRecordsClearlyMarkedAsSynthetic:
    def test_imported_notes_contain_fixture_marker(self) -> None:
        for record in _load(_IMPORTED_PATH):
            notes = record.get("notes", "").lower()
            assert "fixture" in notes or "synthetic" in notes, (
                f"Record {record.get('manufacturer_part_number')} notes: '{notes}'"
            )

    def test_imported_mpns_contain_fixture_prefix(self) -> None:
        for record in _load(_IMPORTED_PATH):
            assert record["manufacturer_part_number"].startswith("FIXTURE-"), (
                f"MPN without FIXTURE- prefix: {record['manufacturer_part_number']}"
            )

    def test_reviewed_notes_contain_pipeline_context(self) -> None:
        for record in _load(_REVIEWED_PATH):
            notes = record.get("review_notes", "").lower()
            assert "not manufacturer catalog" in notes or "synthetic" in notes or "fixture" in notes

    def test_search_results_verification_status_is_sample(self) -> None:
        from grade_engine.tooling_search import load_tooling_records
        for record in [r for r in load_tooling_records() if r["brand"] == _EXPECTED_BRAND]:
            assert record["verification_status"] == "sample_family_level_not_catalog_verified"

    def test_search_results_cutting_data_status_not_imported(self) -> None:
        from grade_engine.tooling_search import load_tooling_records
        for record in [r for r in load_tooling_records() if r["brand"] == _EXPECTED_BRAND]:
            assert record["cutting_data_status"] == "not_imported"
