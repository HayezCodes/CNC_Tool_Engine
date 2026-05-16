"""Tests for grade_engine.recommendation_context.

Covers:
- Context builder functions and normalization
- context_is_active / context_active_notes
- score_machine_context / score_setup_context / score_production_context
- score_context_boosts (combined scoring)
- apply_context_to_candidates re-ranking
- No-context fallback (zero-op when context is empty)
- Stability-safe recommendation behavior
- Exact candidate compatibility (suggest_tool_candidates integration)
- No architecture regressions (existing behavior unchanged without context)
"""
from __future__ import annotations

import pytest

from grade_engine.recommendation_context import (
    apply_context_to_candidates,
    build_machine_context,
    build_production_context,
    build_recommendation_context,
    build_setup_context,
    context_active_notes,
    context_is_active,
    score_context_boosts,
    score_machine_context,
    score_production_context,
    score_setup_context,
)


# ---------------------------------------------------------------------------
# Fixture records
# ---------------------------------------------------------------------------

def _make_record(**kwargs) -> dict:
    base = {
        "brand": "Test Brand",
        "manufacturer_part_number": "TEST-001",
        "tool_category": "endmill",
        "series": "",
        "family_name": "",
        "designation": "",
        "grade": "",
        "chipbreaker": "",
        "coating": "",
        "material_fit": ["P"],
        "operation_fit": ["general_milling"],
        "geometry_tags": [],
        "coolant_capability": "external_only",
        "dimensions": {},
        "holder_compatibility": [],
        "source_label": "Test",
        "source_url": "",
        "source_page_reference": "",
        "verification_status": "sample_family_level_not_catalog_verified",
        "cutting_data_status": "not_imported",
        "notes": "",
    }
    base.update(kwargs)
    return base


ENDMILL = _make_record(tool_category="endmill", coating="AlTiN")
TURNING_INSERT = _make_record(tool_category="turning_insert", chipbreaker="MR")
MILLING_INSERT = _make_record(tool_category="milling_insert")
HIGH_FEED_INSERT = _make_record(tool_category="high_feed_insert", operation_fit=["high_feed_milling"])
BORING_BAR = _make_record(tool_category="boring_bar", geometry_tags=["solid_carbide_shank"])
DRILL = _make_record(tool_category="drill", coolant_capability="through_coolant_capable")
INDEXABLE_DRILL = _make_record(tool_category="indexable_drill", coolant_capability="through_coolant_capable")
TURNING_INSERT_PF = _make_record(tool_category="turning_insert", chipbreaker="PF")
ENDMILL_VAR_HELIX = _make_record(
    tool_category="endmill",
    geometry_tags=["variable_helix", "four_flute"],
    coating="TiAlN",
)
ENDMILL_SOLID_SHANK = _make_record(
    tool_category="endmill",
    geometry_tags=["solid_carbide_shank", "anti_vibration"],
)
CVD_INSERT = _make_record(tool_category="turning_insert", coating="CVD Al2O3", grade="KC5010")


# ---------------------------------------------------------------------------
# Builder / normalization tests
# ---------------------------------------------------------------------------

class TestBuildContexts:
    def test_machine_context_defaults(self):
        m = build_machine_context()
        assert m["machine_type"] == ""
        assert m["spindle_taper"] == ""
        assert m["max_rpm"] == 0
        assert m["through_spindle_coolant"] is None
        assert m["live_tooling"] is None
        assert m["machine_rigidity"] == ""
        assert m["machine_size_class"] == ""

    def test_machine_context_normalizes_case(self):
        m = build_machine_context(machine_type="LATHE", machine_rigidity="HIGH")
        assert m["machine_type"] == "lathe"
        assert m["machine_rigidity"] == "high"

    def test_machine_context_max_rpm_clamped(self):
        m = build_machine_context(max_rpm=18000)
        assert m["max_rpm"] == 18000

    def test_machine_context_bool_fields(self):
        m = build_machine_context(through_spindle_coolant=True, live_tooling=False)
        assert m["through_spindle_coolant"] is True
        assert m["live_tooling"] is False

    def test_setup_context_defaults(self):
        s = build_setup_context()
        for v in s.values():
            assert v == ""

    def test_production_context_defaults(self):
        p = build_production_context()
        for v in p.values():
            assert v == ""

    def test_build_recommendation_context_structure(self):
        ctx = build_recommendation_context()
        assert "machine" in ctx
        assert "setup" in ctx
        assert "production" in ctx

    def test_build_recommendation_context_with_sub_contexts(self):
        m = build_machine_context(machine_type="lathe")
        s = build_setup_context(chatter_risk="high")
        ctx = build_recommendation_context(machine=m, setup=s)
        assert ctx["machine"]["machine_type"] == "lathe"
        assert ctx["setup"]["chatter_risk"] == "high"


# ---------------------------------------------------------------------------
# context_is_active
# ---------------------------------------------------------------------------

class TestContextIsActive:
    def test_empty_context_not_active(self):
        assert not context_is_active(build_recommendation_context())

    def test_none_not_active(self):
        assert not context_is_active(None)

    def test_empty_dict_not_active(self):
        assert not context_is_active({})

    def test_machine_type_activates(self):
        ctx = build_recommendation_context(machine=build_machine_context(machine_type="lathe"))
        assert context_is_active(ctx)

    def test_max_rpm_activates(self):
        ctx = build_recommendation_context(machine=build_machine_context(max_rpm=12000))
        assert context_is_active(ctx)

    def test_zero_rpm_not_active(self):
        ctx = build_recommendation_context(machine=build_machine_context(max_rpm=0))
        assert not context_is_active(ctx)

    def test_tsc_true_activates(self):
        ctx = build_recommendation_context(machine=build_machine_context(through_spindle_coolant=True))
        assert context_is_active(ctx)

    def test_tsc_false_activates(self):
        ctx = build_recommendation_context(machine=build_machine_context(through_spindle_coolant=False))
        assert context_is_active(ctx)

    def test_setup_chatter_activates(self):
        ctx = build_recommendation_context(setup=build_setup_context(chatter_risk="high"))
        assert context_is_active(ctx)

    def test_production_pvp_activates(self):
        ctx = build_recommendation_context(production=build_production_context(prototype_vs_production="production"))
        assert context_is_active(ctx)

    def test_tool_life_priority_activates(self):
        ctx = build_recommendation_context(production=build_production_context(tool_life_priority="high"))
        assert context_is_active(ctx)


# ---------------------------------------------------------------------------
# context_active_notes
# ---------------------------------------------------------------------------

class TestContextActiveNotes:
    def test_no_notes_for_empty_context(self):
        assert context_active_notes(build_recommendation_context()) == []

    def test_no_notes_for_none(self):
        assert context_active_notes(None) == []

    def test_high_rpm_note(self):
        ctx = build_recommendation_context(machine=build_machine_context(max_rpm=18000))
        notes = context_active_notes(ctx)
        assert any("rpm" in n.lower() or "rpm" in n.lower() for n in notes)

    def test_low_rpm_note(self):
        ctx = build_recommendation_context(machine=build_machine_context(max_rpm=3000))
        notes = context_active_notes(ctx)
        assert any("low" in n.lower() for n in notes)

    def test_no_tsc_note(self):
        ctx = build_recommendation_context(machine=build_machine_context(through_spindle_coolant=False))
        notes = context_active_notes(ctx)
        assert any("coolant" in n.lower() for n in notes)

    def test_chatter_risk_note(self):
        ctx = build_recommendation_context(setup=build_setup_context(chatter_risk="high"))
        notes = context_active_notes(ctx)
        assert any("chatter" in n.lower() for n in notes)

    def test_production_note(self):
        ctx = build_recommendation_context(production=build_production_context(prototype_vs_production="production"))
        notes = context_active_notes(ctx)
        assert any("production" in n.lower() for n in notes)

    def test_prototype_note(self):
        ctx = build_recommendation_context(production=build_production_context(prototype_vs_production="prototype"))
        notes = context_active_notes(ctx)
        assert any("prototype" in n.lower() for n in notes)

    def test_bt30_note(self):
        ctx = build_recommendation_context(machine=build_machine_context(spindle_taper="BT30"))
        notes = context_active_notes(ctx)
        assert any("bt30" in n.lower() for n in notes)

    def test_multiple_notes(self):
        ctx = build_recommendation_context(
            machine=build_machine_context(max_rpm=18000, machine_rigidity="high"),
            setup=build_setup_context(chatter_risk="high"),
            production=build_production_context(tool_life_priority="high"),
        )
        assert len(context_active_notes(ctx)) >= 3


# ---------------------------------------------------------------------------
# score_machine_context
# ---------------------------------------------------------------------------

class TestScoreMachineContext:
    def test_no_machine_returns_zero(self):
        assert score_machine_context(ENDMILL, None) == 0.0
        assert score_machine_context(ENDMILL, {}) == 0.0

    def test_high_rpm_boosts_solid_carbide(self):
        m = build_machine_context(max_rpm=18000)
        assert score_machine_context(ENDMILL, m) > 0

    def test_high_rpm_boosts_variable_helix(self):
        m = build_machine_context(max_rpm=18000)
        assert score_machine_context(ENDMILL_VAR_HELIX, m) > score_machine_context(ENDMILL, m)

    def test_high_rpm_penalizes_milling_insert(self):
        m = build_machine_context(max_rpm=18000)
        assert score_machine_context(MILLING_INSERT, m) < score_machine_context(ENDMILL, m)

    def test_low_rpm_boosts_indexable(self):
        m = build_machine_context(max_rpm=2000)
        assert score_machine_context(TURNING_INSERT, m) > 0

    def test_low_rpm_penalizes_endmill(self):
        m = build_machine_context(max_rpm=2000)
        assert score_machine_context(ENDMILL, m) < 0

    def test_tsc_true_boosts_through_coolant_drill(self):
        m = build_machine_context(through_spindle_coolant=True)
        assert score_machine_context(DRILL, m) > 0

    def test_tsc_false_penalizes_through_coolant_drill(self):
        m = build_machine_context(through_spindle_coolant=False)
        assert score_machine_context(DRILL, m) < 0

    def test_tsc_false_no_effect_on_endmill(self):
        m = build_machine_context(through_spindle_coolant=False)
        # Endmill has external_only coolant — no penalty
        assert score_machine_context(ENDMILL, m) == 0.0

    def test_low_rigidity_boosts_anti_vibration(self):
        m = build_machine_context(machine_rigidity="low")
        assert score_machine_context(ENDMILL_SOLID_SHANK, m) > 0

    def test_low_rigidity_penalizes_high_feed(self):
        m = build_machine_context(machine_rigidity="low")
        assert score_machine_context(HIGH_FEED_INSERT, m) < 0

    def test_bt30_boosts_solid_carbide(self):
        m = build_machine_context(spindle_taper="BT30")
        assert score_machine_context(ENDMILL, m) > 0

    def test_bt30_penalizes_milling_insert(self):
        m = build_machine_context(spindle_taper="BT30")
        assert score_machine_context(MILLING_INSERT, m) < 0

    def test_small_machine_boosts_solid_carbide(self):
        m = build_machine_context(machine_size_class="small")
        assert score_machine_context(ENDMILL, m) > 0

    def test_heavy_duty_boosts_indexable(self):
        m = build_machine_context(machine_size_class="heavy_duty")
        assert score_machine_context(TURNING_INSERT, m) > 0


# ---------------------------------------------------------------------------
# score_setup_context
# ---------------------------------------------------------------------------

class TestScoreSetupContext:
    def test_no_setup_returns_zero(self):
        assert score_setup_context(ENDMILL, None) == 0.0
        assert score_setup_context(ENDMILL, {}) == 0.0

    def test_long_stickout_boosts_anti_vibration(self):
        s = build_setup_context(stickout_length="long")
        assert score_setup_context(ENDMILL_SOLID_SHANK, s) > 0

    def test_long_stickout_boosts_boring_bar(self):
        s = build_setup_context(stickout_length="long")
        assert score_setup_context(BORING_BAR, s) > 0

    def test_high_chatter_boosts_anti_vibration(self):
        s = build_setup_context(chatter_risk="high")
        assert score_setup_context(ENDMILL_SOLID_SHANK, s) > 0

    def test_high_chatter_boosts_boring_bar(self):
        s = build_setup_context(chatter_risk="high")
        assert score_setup_context(BORING_BAR, s) > 0

    def test_poor_setup_penalizes_high_feed(self):
        s = build_setup_context(setup_rigidity="poor")
        assert score_setup_context(HIGH_FEED_INSERT, s) < 0

    def test_poor_workholding_penalizes_high_feed(self):
        s = build_setup_context(workholding_rigidity="poor")
        assert score_setup_context(HIGH_FEED_INSERT, s) < 0

    def test_poor_setup_boosts_conservative_chipbreaker(self):
        s = build_setup_context(setup_rigidity="poor")
        assert score_setup_context(TURNING_INSERT, s) > 0  # MR chipbreaker

    def test_shrink_fit_boosts_solid_carbide(self):
        s = build_setup_context(holder_type="shrink_fit")
        assert score_setup_context(ENDMILL, s) > 0

    def test_shrink_fit_no_boost_to_insert(self):
        s = build_setup_context(holder_type="shrink_fit")
        assert score_setup_context(TURNING_INSERT, s) == 0.0

    def test_normal_setup_zero_delta(self):
        s = build_setup_context()
        assert score_setup_context(ENDMILL, s) == 0.0


# ---------------------------------------------------------------------------
# score_production_context
# ---------------------------------------------------------------------------

class TestScoreProductionContext:
    def test_no_production_returns_zero(self):
        assert score_production_context(ENDMILL, None) == 0.0
        assert score_production_context(ENDMILL, {}) == 0.0

    def test_production_boosts_indexable(self):
        p = build_production_context(prototype_vs_production="production")
        assert score_production_context(TURNING_INSERT, p) > 0

    def test_production_penalizes_solid_carbide(self):
        p = build_production_context(prototype_vs_production="production")
        assert score_production_context(ENDMILL, p) < 0

    def test_prototype_boosts_solid_carbide(self):
        p = build_production_context(prototype_vs_production="prototype")
        assert score_production_context(ENDMILL, p) > 0

    def test_prototype_penalizes_turning_insert(self):
        p = build_production_context(prototype_vs_production="prototype")
        assert score_production_context(TURNING_INSERT, p) < 0

    def test_high_tool_life_boosts_wear_resistant_coating(self):
        p = build_production_context(tool_life_priority="high")
        assert score_production_context(CVD_INSERT, p) > 0

    def test_high_tool_life_no_boost_to_uncoated(self):
        p = build_production_context(tool_life_priority="high")
        uncoated = _make_record(tool_category="turning_insert", coating="")
        assert score_production_context(uncoated, p) == 0.0

    def test_cycle_time_boosts_high_feed(self):
        p = build_production_context(cycle_time_priority="high")
        assert score_production_context(HIGH_FEED_INSERT, p) > 0

    def test_cost_priority_boosts_indexable(self):
        p = build_production_context(cost_priority="high")
        assert score_production_context(TURNING_INSERT, p) > 0

    def test_roughing_priority_boosts_high_feed(self):
        p = build_production_context(roughing_vs_finishing_priority="roughing")
        assert score_production_context(HIGH_FEED_INSERT, p) > 0

    def test_roughing_priority_boosts_mr_chipbreaker(self):
        p = build_production_context(roughing_vs_finishing_priority="roughing")
        assert score_production_context(TURNING_INSERT, p) > 0  # MR chipbreaker

    def test_finishing_priority_boosts_pf_chipbreaker(self):
        p = build_production_context(roughing_vs_finishing_priority="finishing")
        assert score_production_context(TURNING_INSERT_PF, p) > 0

    def test_empty_production_zero_for_all(self):
        p = build_production_context()
        for record in (ENDMILL, TURNING_INSERT, HIGH_FEED_INSERT, BORING_BAR):
            assert score_production_context(record, p) == 0.0


# ---------------------------------------------------------------------------
# score_context_boosts (combined)
# ---------------------------------------------------------------------------

class TestScoreContextBoosts:
    def test_no_context_zero(self):
        assert score_context_boosts(ENDMILL, None) == 0.0

    def test_empty_context_zero(self):
        ctx = build_recommendation_context()
        assert score_context_boosts(ENDMILL, ctx) == 0.0

    def test_combines_all_sub_scores(self):
        ctx = build_recommendation_context(
            machine=build_machine_context(max_rpm=18000),
            setup=build_setup_context(chatter_risk="high"),
            production=build_production_context(prototype_vs_production="prototype"),
        )
        # ENDMILL_SOLID_SHANK: solid carbide + anti_vibration tag
        score = score_context_boosts(ENDMILL_SOLID_SHANK, ctx)
        assert score > 0

    def test_conflicting_signals_sum_correctly(self):
        # High RPM boosts solid carbide; production mode penalizes solid carbide
        ctx = build_recommendation_context(
            machine=build_machine_context(max_rpm=18000),
            production=build_production_context(prototype_vs_production="production"),
        )
        sc_boost = score_machine_context(ENDMILL, ctx["machine"])
        sp_boost = score_production_context(ENDMILL, ctx["production"])
        expected = sc_boost + sp_boost
        assert abs(score_context_boosts(ENDMILL, ctx) - expected) < 1e-9

    def test_no_cutting_data_involved(self):
        ctx = build_recommendation_context(
            machine=build_machine_context(max_rpm=15000),
        )
        result = score_context_boosts(DRILL, ctx)
        assert isinstance(result, float)


# ---------------------------------------------------------------------------
# apply_context_to_candidates
# ---------------------------------------------------------------------------

class TestApplyContextToCandidates:
    def _candidates(self):
        return [TURNING_INSERT, ENDMILL, BORING_BAR, HIGH_FEED_INSERT]

    def test_empty_candidates_unchanged(self):
        ctx = build_recommendation_context(machine=build_machine_context(max_rpm=18000))
        assert apply_context_to_candidates([], ctx) == []

    def test_no_context_unchanged(self):
        candidates = self._candidates()
        result = apply_context_to_candidates(candidates, build_recommendation_context())
        assert result == candidates

    def test_none_context_unchanged(self):
        candidates = self._candidates()
        result = apply_context_to_candidates(candidates, None)
        assert result == candidates

    def test_limit_applied(self):
        ctx = build_recommendation_context(machine=build_machine_context(max_rpm=18000))
        result = apply_context_to_candidates(self._candidates(), ctx, limit=2)
        assert len(result) == 2

    def test_prototype_context_promotes_endmill(self):
        ctx = build_recommendation_context(
            production=build_production_context(prototype_vs_production="prototype")
        )
        result = apply_context_to_candidates(self._candidates(), ctx)
        endmill_idx = next(i for i, r in enumerate(result) if r["tool_category"] == "endmill")
        turning_idx = next(i for i, r in enumerate(result) if r["tool_category"] == "turning_insert")
        assert endmill_idx < turning_idx

    def test_production_context_promotes_turning_insert(self):
        ctx = build_recommendation_context(
            production=build_production_context(prototype_vs_production="production")
        )
        result = apply_context_to_candidates(self._candidates(), ctx)
        turning_idx = next(i for i, r in enumerate(result) if r["tool_category"] == "turning_insert")
        endmill_idx = next(i for i, r in enumerate(result) if r["tool_category"] == "endmill")
        assert turning_idx < endmill_idx

    def test_poor_setup_demotes_high_feed(self):
        ctx = build_recommendation_context(
            setup=build_setup_context(setup_rigidity="poor")
        )
        candidates = [HIGH_FEED_INSERT, TURNING_INSERT]
        result = apply_context_to_candidates(candidates, ctx)
        high_feed_idx = next(i for i, r in enumerate(result) if r["tool_category"] == "high_feed_insert")
        assert high_feed_idx > 0  # demoted from first position

    def test_original_order_preserved_for_equal_boost(self):
        # Two identical endmills — same boost, preserve original order
        em1 = _make_record(tool_category="endmill", manufacturer_part_number="EM-001")
        em2 = _make_record(tool_category="endmill", manufacturer_part_number="EM-002")
        ctx = build_recommendation_context(
            machine=build_machine_context(max_rpm=18000)
        )
        result = apply_context_to_candidates([em1, em2], ctx)
        assert result[0]["manufacturer_part_number"] == "EM-001"
        assert result[1]["manufacturer_part_number"] == "EM-002"

    def test_result_is_new_list(self):
        candidates = self._candidates()
        ctx = build_recommendation_context(machine=build_machine_context(max_rpm=18000))
        result = apply_context_to_candidates(candidates, ctx)
        assert result is not candidates


# ---------------------------------------------------------------------------
# Stability-safe recommendation behavior
# ---------------------------------------------------------------------------

class TestStabilitySafeRecommendations:
    def test_weak_setup_does_not_promote_high_feed(self):
        """Poor setup + poor workholding must not surface high_feed_insert at top."""
        ctx = build_recommendation_context(
            setup=build_setup_context(setup_rigidity="poor", workholding_rigidity="poor")
        )
        candidates = [HIGH_FEED_INSERT, TURNING_INSERT, BORING_BAR]
        result = apply_context_to_candidates(candidates, ctx)
        assert result[0]["tool_category"] != "high_feed_insert"

    def test_high_chatter_promotes_anti_vibration(self):
        ctx = build_recommendation_context(
            setup=build_setup_context(chatter_risk="high")
        )
        candidates = [HIGH_FEED_INSERT, ENDMILL_SOLID_SHANK, TURNING_INSERT]
        result = apply_context_to_candidates(candidates, ctx)
        av_idx = next(
            i for i, r in enumerate(result)
            if "anti_vibration" in r.get("geometry_tags", [])
        )
        hf_idx = next(i for i, r in enumerate(result) if r["tool_category"] == "high_feed_insert")
        assert av_idx < hf_idx

    def test_low_machine_rigidity_penalizes_aggressive(self):
        ctx = build_recommendation_context(
            machine=build_machine_context(machine_rigidity="low")
        )
        boost_hf = score_machine_context(HIGH_FEED_INSERT, ctx["machine"])
        boost_av = score_machine_context(ENDMILL_SOLID_SHANK, ctx["machine"])
        assert boost_av > boost_hf


# ---------------------------------------------------------------------------
# No architecture regressions
# ---------------------------------------------------------------------------

class TestNoArchitectureRegressions:
    def test_suggest_tool_candidates_unaffected_without_context(self):
        """Calling suggest_tool_candidates directly returns same results as before."""
        from grade_engine.tooling_search import suggest_tool_candidates
        results = suggest_tool_candidates("external_turning", "P", tool_category="turning_insert", limit=10)
        assert isinstance(results, list)
        for r in results:
            assert r.get("cutting_data_status") == "not_imported"

    def test_suggest_tool_candidates_returns_no_forbidden_keys(self):
        from grade_engine.tooling_search import suggest_tool_candidates
        forbidden = {"feed", "speed", "sfm", "rpm", "ipr", "ipm", "vc", "fz"}
        results = suggest_tool_candidates("drilling", "P", tool_category="drill", limit=10)
        for r in results:
            for k in r:
                for term in forbidden:
                    assert term not in k.lower(), f"Forbidden key '{k}' in result"

    def test_context_module_does_not_import_forbidden_terms(self):
        """The context module must not reference feed/speed fields anywhere."""
        import inspect
        import grade_engine.recommendation_context as mod
        source = inspect.getsource(mod)
        forbidden = ["feed_rate", "sfm", "rpm_calc", "ipr", "ipm", "vc_value", "fz_value"]
        for term in forbidden:
            assert term not in source, f"Forbidden term '{term}' found in recommendation_context source"

    def test_apply_context_does_not_alter_record_data(self):
        """Records must not be mutated by apply_context_to_candidates."""
        import copy
        ctx = build_recommendation_context(
            machine=build_machine_context(max_rpm=18000),
            production=build_production_context(prototype_vs_production="prototype"),
        )
        candidates = [copy.deepcopy(ENDMILL), copy.deepcopy(TURNING_INSERT)]
        original_mpns = [r["manufacturer_part_number"] for r in candidates]
        result = apply_context_to_candidates(candidates, ctx)
        # Original list unchanged
        assert [r["manufacturer_part_number"] for r in candidates] == original_mpns
        # Result records have same data
        for r in result:
            assert r.get("cutting_data_status") == "not_imported"

    def test_context_boost_bounded(self):
        """Total boost should stay within a reasonable range to not dominate scoring."""
        extreme_ctx = build_recommendation_context(
            machine=build_machine_context(max_rpm=30000, machine_rigidity="high", machine_size_class="heavy_duty"),
            setup=build_setup_context(chatter_risk="high", stickout_length="long"),
            production=build_production_context(prototype_vs_production="prototype", tool_life_priority="high"),
        )
        max_boost = max(
            abs(score_context_boosts(r, extreme_ctx))
            for r in (ENDMILL, TURNING_INSERT, HIGH_FEED_INSERT, BORING_BAR, DRILL, CVD_INSERT)
        )
        # Context boosts should stay under 8 total to remain supplemental
        assert max_boost < 8.0

    def test_zero_context_produces_zero_boost_for_all_categories(self):
        ctx = build_recommendation_context()
        for record in (ENDMILL, TURNING_INSERT, MILLING_INSERT, HIGH_FEED_INSERT, BORING_BAR, DRILL):
            assert score_context_boosts(record, ctx) == 0.0
