"""Integration tests for the Mitsubishi Materials adapter-to-search pipeline.

Proves the full flow:
    adapter output → import → audit → review → searchable tooling records

All records tested here are synthetic fixtures, clearly marked as not manufacturer
catalog data.  No feeds, speeds, or dimensions are expected at any stage.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

# ── Paths ──────────────────────────────────────────────────────────────────────

_REPO = Path(__file__).resolve().parent.parent
_ADAPTER_OUTPUT = (
    _REPO / "tools" / "tooling_adapters" / "output" / "mitsubishi_materials_sample_records.json"
)
_IMPORTED_PATH = (
    _REPO / "tool_data" / "tooling_search" / "records" / "mitsubishi_materials_imported_tools.json"
)
_REVIEWED_PATH = (
    _REPO
    / "tool_data"
    / "tooling_search"
    / "records"
    / "reviewed"
    / "mitsubishi_materials_reviewed_tools.json"
)

_EXPECTED_MPN_SET = {
    "FIXTURE-MMC-TI-001",
    "FIXTURE-MMC-TI-002",
    "FIXTURE-MMC-MI-003",
    "FIXTURE-MMC-EM-004",
    "FIXTURE-MMC-IDR-005",
    "FIXTURE-MMC-GRV-006",
    "FIXTURE-MMC-THR-007",
}
_EXPECTED_BRAND = "Mitsubishi Materials Corporation"
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
        assert len(records) == 7

    def test_adapter_output_passes_import_validation(self) -> None:
        from tools.import_tooling_records import validate_import_rows
        records = _load(_ADAPTER_OUTPUT)
        errors = validate_import_rows(records)
        assert errors == [], f"Import validation errors: {errors}"

    def test_adapter_output_has_no_forbidden_keys(self) -> None:
        records = _load(_ADAPTER_OUTPUT)
        for record in records:
            for key in record:
                for term in _FORBIDDEN_TERMS:
                    assert term not in key.lower(), (
                        f"Forbidden key '{key}' found in adapter output record "
                        f"{record.get('manufacturer_part_number', '?')}"
                    )

    def test_adapter_output_all_brands_are_mitsubishi(self) -> None:
        records = _load(_ADAPTER_OUTPUT)
        for record in records:
            assert record["brand"] == _EXPECTED_BRAND

    def test_adapter_output_cutting_data_status_always_not_imported(self) -> None:
        records = _load(_ADAPTER_OUTPUT)
        for record in records:
            assert record["cutting_data_status"] == "not_imported"

    def test_adapter_output_verification_status_is_sample(self) -> None:
        records = _load(_ADAPTER_OUTPUT)
        for record in records:
            assert record["verification_status"] == "sample_family_level_not_catalog_verified"

    def test_adapter_output_dimensions_always_empty(self) -> None:
        records = _load(_ADAPTER_OUTPUT)
        for record in records:
            assert record["dimensions"] == {}


# ── Stage 2: Imported records exist and audit cleanly ─────────────────────────

class TestImportedRecordsAuditCleanly:
    def test_imported_file_exists(self) -> None:
        assert _IMPORTED_PATH.exists(), f"Imported records not found: {_IMPORTED_PATH}"

    def test_imported_file_is_json_list(self) -> None:
        records = _load(_IMPORTED_PATH)
        assert isinstance(records, list)
        assert len(records) == 7

    def test_imported_mpns_match_expected(self) -> None:
        records = _load(_IMPORTED_PATH)
        mpns = {r["manufacturer_part_number"] for r in records}
        assert mpns == _EXPECTED_MPN_SET

    def test_imported_records_have_all_schema_fields(self) -> None:
        from grade_engine.tooling_search import SCHEMA_FIELDS
        records = _load(_IMPORTED_PATH)
        for record in records:
            missing = [f for f in SCHEMA_FIELDS if f not in record]
            assert not missing, (
                f"Record {record.get('manufacturer_part_number')} missing: {missing}"
            )

    def test_imported_records_audit_zero_issues(self) -> None:
        from tools.audit_tooling_search_records import audit_record
        records = _load(_IMPORTED_PATH)
        for idx, record in enumerate(records):
            issues = audit_record(record, idx, _IMPORTED_PATH.name)
            assert issues == [], (
                f"Audit issues in record {record.get('manufacturer_part_number')}: {issues}"
            )

    def test_imported_records_cutting_data_status(self) -> None:
        records = _load(_IMPORTED_PATH)
        for record in records:
            assert record["cutting_data_status"] == "not_imported"

    def test_imported_records_verification_status(self) -> None:
        records = _load(_IMPORTED_PATH)
        for record in records:
            assert record["verification_status"] == "sample_family_level_not_catalog_verified"

    def test_imported_records_no_forbidden_keys(self) -> None:
        records = _load(_IMPORTED_PATH)
        for record in records:
            for key in record:
                for term in _FORBIDDEN_TERMS:
                    assert term not in key.lower(), (
                        f"Forbidden key '{key}' in imported record "
                        f"{record.get('manufacturer_part_number', '?')}"
                    )

    def test_imported_records_dimensions_empty(self) -> None:
        records = _load(_IMPORTED_PATH)
        for record in records:
            assert record["dimensions"] == {}

    def test_imported_records_material_fit_only_iso_codes(self) -> None:
        valid_codes = {"P", "M", "K", "N", "S", "H"}
        records = _load(_IMPORTED_PATH)
        for record in records:
            for code in record.get("material_fit", []):
                assert code in valid_codes, (
                    f"Non-ISO material code '{code}' in {record.get('manufacturer_part_number')}"
                )

    def test_imported_records_list_fields_are_lists(self) -> None:
        list_fields = ["material_fit", "operation_fit", "geometry_tags", "holder_compatibility"]
        records = _load(_IMPORTED_PATH)
        for record in records:
            for field in list_fields:
                assert isinstance(record.get(field), list), (
                    f"Field '{field}' not a list in {record.get('manufacturer_part_number')}"
                )

    def test_imported_records_source_url_present(self) -> None:
        records = _load(_IMPORTED_PATH)
        for record in records:
            assert record.get("source_url", "").strip()

    def test_imported_records_source_label_present(self) -> None:
        records = _load(_IMPORTED_PATH)
        for record in records:
            assert record.get("source_label", "").strip()


# ── Stage 3: Reviewed records are correctly promoted ─────────────────────────

class TestReviewedRecordsCorrectlyPromoted:
    def test_reviewed_file_exists(self) -> None:
        assert _REVIEWED_PATH.exists(), f"Reviewed records not found: {_REVIEWED_PATH}"

    def test_reviewed_file_is_json_list(self) -> None:
        records = _load(_REVIEWED_PATH)
        assert isinstance(records, list)
        assert len(records) == 7

    def test_reviewed_mpns_match_expected(self) -> None:
        records = _load(_REVIEWED_PATH)
        mpns = {r["manufacturer_part_number"] for r in records}
        assert mpns == _EXPECTED_MPN_SET

    def test_reviewed_status_is_family_level_candidate(self) -> None:
        records = _load(_REVIEWED_PATH)
        for record in records:
            assert record["verification_status"] == "reviewed_family_level_candidate"

    def test_reviewed_cutting_data_status_unchanged(self) -> None:
        records = _load(_REVIEWED_PATH)
        for record in records:
            assert record["cutting_data_status"] == "not_imported"

    def test_reviewed_reviewer_field_set(self) -> None:
        records = _load(_REVIEWED_PATH)
        for record in records:
            assert record.get("reviewer") == "Joshua Hayes"

    def test_reviewed_review_date_set(self) -> None:
        records = _load(_REVIEWED_PATH)
        for record in records:
            assert record.get("review_date", "").strip()

    def test_reviewed_review_notes_present(self) -> None:
        records = _load(_REVIEWED_PATH)
        for record in records:
            notes = record.get("review_notes", "")
            assert "pipeline" in notes.lower() or "fixture" in notes.lower(), (
                f"review_notes missing pipeline/fixture context: '{notes}'"
            )

    def test_reviewed_records_no_forbidden_keys(self) -> None:
        records = _load(_REVIEWED_PATH)
        for record in records:
            for key in record:
                for term in _FORBIDDEN_TERMS:
                    assert term not in key.lower(), (
                        f"Forbidden key '{key}' in reviewed record "
                        f"{record.get('manufacturer_part_number', '?')}"
                    )

    def test_reviewed_records_dimensions_empty(self) -> None:
        records = _load(_REVIEWED_PATH)
        for record in records:
            assert record.get("dimensions") == {}

    def test_reviewed_records_audit_clean(self) -> None:
        from tools.audit_tooling_search_records import audit_record, VALID_VERIFICATION_STATUSES
        assert "reviewed_family_level_candidate" in VALID_VERIFICATION_STATUSES
        records = _load(_REVIEWED_PATH)
        for idx, record in enumerate(records):
            issues = audit_record(record, idx, _REVIEWED_PATH.name)
            assert issues == [], (
                f"Audit issues in reviewed record "
                f"{record.get('manufacturer_part_number')}: {issues}"
            )


# ── Stage 4: Mitsubishi records searchable via tooling_search ─────────────────

class TestMitsubishiRecordsSearchable:
    def test_mitsubishi_records_in_load_tooling_records(self) -> None:
        from grade_engine.tooling_search import load_tooling_records
        all_records = load_tooling_records()
        mitsu = [r for r in all_records if r["brand"] == _EXPECTED_BRAND]
        assert len(mitsu) == 7

    def test_mitsubishi_mpns_all_present_in_search_index(self) -> None:
        from grade_engine.tooling_search import load_tooling_records
        all_records = load_tooling_records()
        indexed_mpns = {r["manufacturer_part_number"] for r in all_records if r["brand"] == _EXPECTED_BRAND}
        assert indexed_mpns == _EXPECTED_MPN_SET

    def test_search_by_mitsubishi_brand_returns_records(self) -> None:
        from grade_engine.tooling_search import search_tooling_records
        results = search_tooling_records("Mitsubishi")
        assert results
        assert all(r["brand"] == _EXPECTED_BRAND for r in results)

    def test_search_by_mitsubishi_returns_all_7(self) -> None:
        from grade_engine.tooling_search import search_tooling_records
        results = search_tooling_records("Mitsubishi Materials")
        assert len(results) == 7

    def test_filter_by_mitsubishi_brand_returns_correct_records(self) -> None:
        from grade_engine.tooling_search import load_tooling_records, filter_tooling_records
        results = filter_tooling_records(load_tooling_records(), {"brand": "mitsubishi"})
        assert len(results) == 7
        assert all(r["brand"] == _EXPECTED_BRAND for r in results)

    def test_filter_mitsubishi_turning_inserts(self) -> None:
        from grade_engine.tooling_search import load_tooling_records, filter_tooling_records
        results = filter_tooling_records(
            load_tooling_records(),
            {"brand": "mitsubishi", "tool_category": "turning_insert"},
        )
        assert len(results) == 2
        assert all(r["tool_category"] == "turning_insert" for r in results)

    def test_filter_mitsubishi_by_material_group_p(self) -> None:
        from grade_engine.tooling_search import load_tooling_records, filter_tooling_records
        results = filter_tooling_records(
            load_tooling_records(),
            {"brand": "mitsubishi", "material_group": "P"},
        )
        assert results
        assert all("P" in r["material_fit"] for r in results)

    def test_search_by_mitsubishi_mpn(self) -> None:
        from grade_engine.tooling_search import search_tooling_records
        results = search_tooling_records("FIXTURE-MMC-TI-001")
        assert results
        assert results[0]["manufacturer_part_number"] == "FIXTURE-MMC-TI-001"

    def test_explain_tool_match_returns_reasons_for_mitsubishi(self) -> None:
        from grade_engine.tooling_search import search_tooling_records, explain_tool_match
        results = search_tooling_records("Mitsubishi")
        assert results
        reasons = explain_tool_match(results[0], "Mitsubishi")
        assert reasons
        assert any("brand" in r.lower() or "mitsubishi" in r.lower() for r in reasons)

    def test_mitsubishi_records_have_required_display_fields(self) -> None:
        from grade_engine.tooling_search import load_tooling_records
        mitsu = [r for r in load_tooling_records() if r["brand"] == _EXPECTED_BRAND]
        for record in mitsu:
            assert "brand" in record
            assert "manufacturer_part_number" in record
            assert "tool_category" in record
            assert isinstance(record.get("material_fit"), list)
            assert isinstance(record.get("operation_fit"), list)
            assert "verification_status" in record
            assert "cutting_data_status" in record


# ── Stage 5: No feeds/speeds at any stage ────────────────────────────────────

class TestNoFeedsOrSpeedsAtAnyStage:
    def _check_no_forbidden_keys(self, records: list[dict], stage: str) -> None:
        for record in records:
            for key in record:
                for term in _FORBIDDEN_TERMS:
                    assert term not in key.lower(), (
                        f"Forbidden key '{key}' found at {stage} stage in record "
                        f"{record.get('manufacturer_part_number', '?')}"
                    )

    def test_adapter_output_no_forbidden_keys(self) -> None:
        self._check_no_forbidden_keys(_load(_ADAPTER_OUTPUT), "adapter_output")

    def test_imported_no_forbidden_keys(self) -> None:
        self._check_no_forbidden_keys(_load(_IMPORTED_PATH), "imported")

    def test_reviewed_no_forbidden_keys(self) -> None:
        self._check_no_forbidden_keys(_load(_REVIEWED_PATH), "reviewed")

    def test_search_index_mitsubishi_records_no_forbidden_keys(self) -> None:
        from grade_engine.tooling_search import load_tooling_records
        mitsu = [r for r in load_tooling_records() if r["brand"] == _EXPECTED_BRAND]
        self._check_no_forbidden_keys(mitsu, "search_index")

    def test_no_forbidden_terms_in_serialized_records_text(self) -> None:
        text = _IMPORTED_PATH.read_text(encoding="utf-8").lower()
        for term in ("feed_rate", "spindle_speed", "sfm_value", "rpm_value"):
            assert term not in text, f"Suspicious key pattern '{term}' found in imported records"


# ── Stage 6: Records clearly marked as synthetic ──────────────────────────────

class TestRecordsClearlyMarkedAsSynthetic:
    def test_imported_notes_contain_fixture_marker(self) -> None:
        records = _load(_IMPORTED_PATH)
        for record in records:
            notes = record.get("notes", "").lower()
            assert "fixture" in notes or "synthetic" in notes, (
                f"Record {record.get('manufacturer_part_number')} notes do not mark as fixture: '{notes}'"
            )

    def test_imported_mpns_contain_fixture_prefix(self) -> None:
        records = _load(_IMPORTED_PATH)
        for record in records:
            assert record["manufacturer_part_number"].startswith("FIXTURE-"), (
                f"MPN does not have FIXTURE- prefix: {record['manufacturer_part_number']}"
            )

    def test_reviewed_notes_contain_pipeline_context(self) -> None:
        records = _load(_REVIEWED_PATH)
        for record in records:
            notes = record.get("review_notes", "").lower()
            assert "not manufacturer catalog" in notes or "synthetic" in notes or "fixture" in notes

    def test_search_results_verification_status_is_sample(self) -> None:
        from grade_engine.tooling_search import load_tooling_records
        mitsu = [r for r in load_tooling_records() if r["brand"] == _EXPECTED_BRAND]
        for record in mitsu:
            assert record["verification_status"] == "sample_family_level_not_catalog_verified"

    def test_search_results_cutting_data_status_not_imported(self) -> None:
        from grade_engine.tooling_search import load_tooling_records
        mitsu = [r for r in load_tooling_records() if r["brand"] == _EXPECTED_BRAND]
        for record in mitsu:
            assert record["cutting_data_status"] == "not_imported"
