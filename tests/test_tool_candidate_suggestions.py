"""Tests for suggest_tool_candidates() in grade_engine.tooling_search.

Covers: operation/material filtering, tool_category/brand optional filters,
limit enforcement, field completeness, no forbidden feed/speed fields.
"""
from __future__ import annotations

import pytest

from grade_engine.tooling_search import (
    SCHEMA_FIELDS,
    load_tooling_records,
    suggest_tool_candidates,
)

FORBIDDEN_TERMS = ("feed", "speed", "sfm", "rpm", "ipr", "ipm", "vc", "fz")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _all_records_have_field(records, field):
    return all(field in r for r in records)


def _no_forbidden_key(record):
    for key in record:
        key_lower = key.lower()
        for term in FORBIDDEN_TERMS:
            if term in key_lower:
                return False
    return True


# ── Baseline: index is populated ─────────────────────────────────────────────

def test_tooling_index_has_records():
    records = load_tooling_records()
    assert len(records) >= 1


# ── suggest_tool_candidates: turning ─────────────────────────────────────────

def test_turning_returns_turning_insert_candidates():
    results = suggest_tool_candidates("external_turning", "P", tool_category="turning_insert")
    # Should return only turning_insert records (or empty if none matched)
    for r in results:
        assert r["tool_category"] == "turning_insert"


def test_turning_facing_operation():
    results = suggest_tool_candidates("facing", "M", tool_category="turning_insert")
    for r in results:
        assert r["tool_category"] == "turning_insert"


def test_turning_profiling_operation():
    results = suggest_tool_candidates("profiling", "K", tool_category="turning_insert")
    for r in results:
        assert r["tool_category"] == "turning_insert"


# ── suggest_tool_candidates: drilling ────────────────────────────────────────

def test_drilling_returns_drill_candidates():
    results = suggest_tool_candidates("drilling", "P", tool_category="drill")
    for r in results:
        assert r["tool_category"] == "drill"


def test_indexable_drill_category_filter():
    results = suggest_tool_candidates("drilling", "P", tool_category="indexable_drill")
    for r in results:
        assert r["tool_category"] == "indexable_drill"


# ── suggest_tool_candidates: milling ─────────────────────────────────────────

def test_endmill_candidates_have_endmill_category():
    results = suggest_tool_candidates("general_milling", "P", tool_category="endmill")
    for r in results:
        assert r["tool_category"] == "endmill"


def test_milling_insert_candidates():
    results = suggest_tool_candidates("face_milling", "K", tool_category="milling_insert")
    for r in results:
        assert r["tool_category"] == "milling_insert"


def test_shoulder_milling_operation():
    results = suggest_tool_candidates("shoulder_milling", "M", tool_category="milling_insert")
    for r in results:
        assert r["tool_category"] == "milling_insert"


# ── suggest_tool_candidates: grooving ────────────────────────────────────────

def test_grooving_returns_grooving_insert_candidates():
    results = suggest_tool_candidates("grooving", "P", tool_category="grooving_insert")
    for r in results:
        assert r["tool_category"] == "grooving_insert"


def test_parting_operation():
    results = suggest_tool_candidates("parting", "M", tool_category="grooving_insert")
    for r in results:
        assert r["tool_category"] == "grooving_insert"


# ── suggest_tool_candidates: threading ───────────────────────────────────────

def test_external_threading_returns_threading_insert_candidates():
    results = suggest_tool_candidates("external_threading", "P", tool_category="threading_insert")
    for r in results:
        assert r["tool_category"] == "threading_insert"


def test_internal_threading_operation():
    results = suggest_tool_candidates("internal_threading", "M", tool_category="threading_insert")
    for r in results:
        assert r["tool_category"] == "threading_insert"


# ── Material filter ───────────────────────────────────────────────────────────

def test_material_filter_p_steel():
    results = suggest_tool_candidates("external_turning", "P")
    for r in results:
        assert "P" in r["material_fit"]


def test_material_filter_m_stainless():
    results = suggest_tool_candidates("external_turning", "M")
    for r in results:
        assert "M" in r["material_fit"]


def test_material_filter_k_cast_iron():
    results = suggest_tool_candidates("external_turning", "K")
    for r in results:
        assert "K" in r["material_fit"]


# ── Limit enforcement ─────────────────────────────────────────────────────────

def test_limit_default_is_five():
    all_records = load_tooling_records()
    if len(all_records) < 2:
        pytest.skip("not enough records to test limit")
    # Use no tool_category filter to get maximum matches
    results = suggest_tool_candidates("drilling", "P")
    assert len(results) <= 5


def test_limit_custom():
    results = suggest_tool_candidates("external_turning", "P", tool_category="turning_insert", limit=2)
    assert len(results) <= 2


def test_limit_one():
    results = suggest_tool_candidates("drilling", "P", limit=1)
    assert len(results) <= 1


def test_limit_zero_returns_empty():
    results = suggest_tool_candidates("drilling", "P", limit=0)
    assert results == []


# ── No forbidden feed/speed fields in output ──────────────────────────────────

def test_no_forbidden_field_names_in_turning_results():
    results = suggest_tool_candidates("external_turning", "P", tool_category="turning_insert")
    for record in results:
        assert _no_forbidden_key(record), f"Forbidden key found in record: {list(record.keys())}"


def test_no_forbidden_field_names_in_drilling_results():
    results = suggest_tool_candidates("drilling", "P", tool_category="drill")
    for record in results:
        assert _no_forbidden_key(record), f"Forbidden key found in record: {list(record.keys())}"


def test_no_forbidden_field_names_in_milling_results():
    results = suggest_tool_candidates("general_milling", "P", tool_category="endmill")
    for record in results:
        assert _no_forbidden_key(record), f"Forbidden key found in record: {list(record.keys())}"


def test_no_forbidden_field_names_in_grooving_results():
    results = suggest_tool_candidates("grooving", "P", tool_category="grooving_insert")
    for record in results:
        assert _no_forbidden_key(record), f"Forbidden key found in record: {list(record.keys())}"


def test_no_forbidden_field_names_in_threading_results():
    results = suggest_tool_candidates("external_threading", "P", tool_category="threading_insert")
    for record in results:
        assert _no_forbidden_key(record), f"Forbidden key found in record: {list(record.keys())}"


# ── verification_status and cutting_data_status present ──────────────────────

def test_verification_status_present_in_all_results():
    results = suggest_tool_candidates("external_turning", "P", tool_category="turning_insert")
    for r in results:
        assert "verification_status" in r
        assert r["verification_status"]


def test_cutting_data_status_present_in_all_results():
    results = suggest_tool_candidates("external_turning", "P", tool_category="turning_insert")
    for r in results:
        assert "cutting_data_status" in r
        assert r["cutting_data_status"] == "not_imported"


def test_cutting_data_status_not_imported_for_drilling():
    results = suggest_tool_candidates("drilling", "P", tool_category="drill")
    for r in results:
        assert r.get("cutting_data_status") == "not_imported"


# ── Impossible combination returns empty list ─────────────────────────────────

def test_impossible_combination_returns_empty():
    results = suggest_tool_candidates(
        "zzz_nonexistent_operation_xyz",
        "P",
        tool_category="turning_insert",
    )
    assert results == []


def test_impossible_material_returns_empty():
    results = suggest_tool_candidates(
        "external_turning",
        "ZZZZZ_NONEXISTENT_MATERIAL",
        tool_category="turning_insert",
    )
    assert results == []


def test_impossible_brand_returns_empty():
    results = suggest_tool_candidates(
        "drilling",
        "P",
        brand="zzz_no_such_brand_xyz",
    )
    assert results == []


# ── Schema fields present in output ──────────────────────────────────────────

def test_schema_fields_present_in_all_results():
    results = suggest_tool_candidates("drilling", "P")
    for r in results:
        for field in SCHEMA_FIELDS:
            assert field in r, f"Schema field '{field}' missing from candidate record"


# ── Brand filter ──────────────────────────────────────────────────────────────

def test_brand_filter_narrows_results():
    all_results = suggest_tool_candidates("external_turning", "P", tool_category="turning_insert", limit=5)
    if not all_results:
        pytest.skip("no turning_insert / P results in index to test brand filter")
    first_brand = all_results[0]["brand"]
    brand_filtered = suggest_tool_candidates(
        "external_turning", "P", tool_category="turning_insert", brand=first_brand, limit=5
    )
    for r in brand_filtered:
        assert first_brand.lower() in r["brand"].lower()


# ── Return type ───────────────────────────────────────────────────────────────

def test_returns_list():
    results = suggest_tool_candidates("drilling", "P")
    assert isinstance(results, list)


def test_each_result_is_dict():
    results = suggest_tool_candidates("drilling", "P")
    for r in results:
        assert isinstance(r, dict)
