"""Lightweight recommendation context layer.

Provides optional Machine, Setup, and Production context that can boost or
penalize Exact Tool Candidate Suggestions without replacing any existing
recommendation math. All scoring helpers return small deltas (typically -3 to +3)
that are layered on top of the existing tooling_search match scores.

No feeds, speeds, or cutting data are imported or used at any stage.
Calling code that does not supply a context receives unchanged behavior.
"""
from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Valid option sets (also used by the UI layer for selectbox choices)
# ---------------------------------------------------------------------------

MACHINE_TYPES = ("", "machining_center", "lathe", "swiss", "mill_turn", "gantry")
SPINDLE_TAPERS = ("", "BT30", "BT40", "BT50", "CAT30", "CAT40", "CAT50", "HSK63A", "HSK100A", "CAPTO")
MACHINE_RIGIDITY_OPTIONS = ("", "low", "medium", "high")
MACHINE_SIZE_OPTIONS = ("", "small", "medium", "large", "heavy_duty")

STICKOUT_OPTIONS = ("", "short", "normal", "long")
HOLDER_TYPE_OPTIONS = ("", "er_collet", "hydraulic", "shrink_fit", "milling_chuck", "capto")
RIGIDITY_OPTIONS = ("", "good", "average", "poor")
CHATTER_RISK_OPTIONS = ("", "low", "moderate", "high")
TOOL_REACH_OPTIONS = ("", "standard", "extended")

PROTOTYPE_VS_PRODUCTION_OPTIONS = ("", "prototype", "mixed", "production")
ROUGHING_VS_FINISHING_OPTIONS = ("", "roughing", "balanced", "finishing")
PRIORITY_LEVEL_OPTIONS = ("", "low", "standard", "high")


# ---------------------------------------------------------------------------
# Context builders
# ---------------------------------------------------------------------------

def build_machine_context(
    machine_type: str = "",
    spindle_taper: str = "",
    max_rpm: int = 0,
    through_spindle_coolant: bool | None = None,
    live_tooling: bool | None = None,
    machine_rigidity: str = "",
    machine_size_class: str = "",
) -> dict[str, Any]:
    """Build a normalized machine context dict."""
    return {
        "machine_type": str(machine_type or "").lower().strip(),
        "spindle_taper": str(spindle_taper or "").strip(),
        "max_rpm": max(0, int(max_rpm)) if max_rpm else 0,
        "through_spindle_coolant": through_spindle_coolant,
        "live_tooling": live_tooling,
        "machine_rigidity": str(machine_rigidity or "").lower().strip(),
        "machine_size_class": str(machine_size_class or "").lower().strip(),
    }


def build_setup_context(
    stickout_length: str = "",
    holder_type: str = "",
    workholding_rigidity: str = "",
    setup_rigidity: str = "",
    chatter_risk: str = "",
    tool_reach_priority: str = "",
) -> dict[str, Any]:
    """Build a normalized setup context dict."""
    return {
        "stickout_length": str(stickout_length or "").lower().strip(),
        "holder_type": str(holder_type or "").lower().strip(),
        "workholding_rigidity": str(workholding_rigidity or "").lower().strip(),
        "setup_rigidity": str(setup_rigidity or "").lower().strip(),
        "chatter_risk": str(chatter_risk or "").lower().strip(),
        "tool_reach_priority": str(tool_reach_priority or "").lower().strip(),
    }


def build_production_context(
    prototype_vs_production: str = "",
    roughing_vs_finishing_priority: str = "",
    tool_life_priority: str = "",
    surface_finish_priority: str = "",
    cycle_time_priority: str = "",
    cost_priority: str = "",
) -> dict[str, Any]:
    """Build a normalized production context dict."""
    return {
        "prototype_vs_production": str(prototype_vs_production or "").lower().strip(),
        "roughing_vs_finishing_priority": str(roughing_vs_finishing_priority or "").lower().strip(),
        "tool_life_priority": str(tool_life_priority or "").lower().strip(),
        "surface_finish_priority": str(surface_finish_priority or "").lower().strip(),
        "cycle_time_priority": str(cycle_time_priority or "").lower().strip(),
        "cost_priority": str(cost_priority or "").lower().strip(),
    }


def build_recommendation_context(
    machine: dict[str, Any] | None = None,
    setup: dict[str, Any] | None = None,
    production: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Combine sub-contexts into a single recommendation context dict."""
    return {
        "machine": machine if machine is not None else build_machine_context(),
        "setup": setup if setup is not None else build_setup_context(),
        "production": production if production is not None else build_production_context(),
    }


# ---------------------------------------------------------------------------
# Context activity checks
# ---------------------------------------------------------------------------

def context_is_active(ctx: dict[str, Any] | None) -> bool:
    """Return True if any context field has a non-default (non-empty) value."""
    if not ctx:
        return False
    machine = ctx.get("machine") or {}
    setup = ctx.get("setup") or {}
    production = ctx.get("production") or {}

    if machine.get("machine_type") or machine.get("spindle_taper"):
        return True
    if machine.get("max_rpm", 0) > 0:
        return True
    if machine.get("through_spindle_coolant") is not None:
        return True
    if machine.get("live_tooling") is not None:
        return True
    if machine.get("machine_rigidity") or machine.get("machine_size_class"):
        return True

    if setup.get("stickout_length") or setup.get("holder_type"):
        return True
    if setup.get("workholding_rigidity") or setup.get("setup_rigidity"):
        return True
    if setup.get("chatter_risk") or setup.get("tool_reach_priority"):
        return True

    for key in (
        "prototype_vs_production",
        "roughing_vs_finishing_priority",
        "tool_life_priority",
        "surface_finish_priority",
        "cycle_time_priority",
        "cost_priority",
    ):
        if production.get(key):
            return True

    return False


def context_active_notes(ctx: dict[str, Any] | None) -> list[str]:
    """Return human-readable notes describing active context constraints."""
    if not ctx or not context_is_active(ctx):
        return []

    notes: list[str] = []
    machine = ctx.get("machine") or {}
    setup = ctx.get("setup") or {}
    production = ctx.get("production") or {}

    max_rpm = machine.get("max_rpm", 0)
    if max_rpm >= 15000:
        notes.append(f"High-RPM machine ({max_rpm:,} RPM): solid carbide families boosted")
    elif max_rpm > 0 and max_rpm < 4000:
        notes.append(f"Low-RPM machine ({max_rpm:,} RPM): indexable systems preferred")

    tsc = machine.get("through_spindle_coolant")
    if tsc is True:
        notes.append("Through-spindle coolant: through-coolant drills boosted")
    elif tsc is False:
        notes.append("No through-spindle coolant: reduced priority for coolant-dependent deep drilling")

    rigidity = machine.get("machine_rigidity", "")
    if rigidity == "low":
        notes.append("Low machine rigidity: stable, chatter-resistant geometries preferred")
    elif rigidity == "high":
        notes.append("High machine rigidity: high-performance families applicable")

    taper = machine.get("spindle_taper", "")
    if taper in ("BT30", "CAT30"):
        notes.append(f"{taper} spindle: lighter solid-carbide tooling preferred")

    size = machine.get("machine_size_class", "")
    if size == "small":
        notes.append("Small machine: solid carbide and compact indexable systems preferred")
    elif size == "heavy_duty":
        notes.append("Heavy-duty machine: large indexable systems fully applicable")

    stickout = setup.get("stickout_length", "")
    if stickout == "long":
        notes.append("Long stickout: vibration-damped and anti-chatter families boosted")

    chatter = setup.get("chatter_risk", "")
    if chatter == "high":
        notes.append("High chatter risk: anti-vibration geometries and boring bars boosted")

    s_rig = setup.get("setup_rigidity", "")
    if s_rig == "poor":
        notes.append("Poor setup rigidity: conservative geometry families preferred")
    elif s_rig == "good":
        notes.append("Good setup rigidity: aggressive geometry families applicable")

    pvp = production.get("prototype_vs_production", "")
    if pvp == "production":
        notes.append("Production run: durable indexable families preferred")
    elif pvp == "prototype":
        notes.append("Prototype / low-volume: flexible solid carbide tooling preferred")

    tl = production.get("tool_life_priority", "")
    if tl == "high":
        notes.append("High tool-life priority: wear-resistant coatings and grades boosted")

    ct = production.get("cycle_time_priority", "")
    if ct == "high":
        notes.append("Cycle-time priority: high-feed capable families boosted")

    cost = production.get("cost_priority", "")
    if cost == "high":
        notes.append("Cost priority: indexable systems preferred over solid carbide")

    return notes


# ---------------------------------------------------------------------------
# Record property helpers (internal)
# ---------------------------------------------------------------------------

def _is_solid_carbide_tool(record: dict[str, Any]) -> bool:
    return record.get("tool_category", "") in (
        "endmill", "drill", "thread_mill", "reamer", "countersink", "step_drill",
    )


def _is_boring_bar(record: dict[str, Any]) -> bool:
    return record.get("tool_category", "") == "boring_bar"


def _is_indexable_insert(record: dict[str, Any]) -> bool:
    return record.get("tool_category", "") in (
        "turning_insert", "milling_insert", "high_feed_insert",
        "grooving_insert", "threading_insert", "indexable_drill",
    )


def _has_geometry_tag(record: dict[str, Any], *tags: str) -> bool:
    record_tags = set(record.get("geometry_tags") or [])
    return bool(record_tags.intersection(tags))


def _coolant_is_through(record: dict[str, Any]) -> bool:
    return "through_coolant" in str(record.get("coolant_capability", "")).lower()


def _coating_is_wear_resistant(record: dict[str, Any]) -> bool:
    combined = (
        str(record.get("coating", "")).lower()
        + " "
        + str(record.get("grade", "")).lower()
    )
    return any(
        t in combined
        for t in ("cvd", "al2o3", "tialn", "tialsin", "altin", "alcrn", "ticaln")
    )


def _is_high_feed(record: dict[str, Any]) -> bool:
    return record.get("tool_category", "") == "high_feed_insert" or "high_feed_milling" in (
        record.get("operation_fit") or []
    )


# ---------------------------------------------------------------------------
# Sub-context scoring
# ---------------------------------------------------------------------------

def score_machine_context(record: dict[str, Any], machine: dict[str, Any] | None) -> float:
    """Return boost/penalty delta based on machine context. Range: -3 to +3."""
    if not machine:
        return 0.0
    delta = 0.0

    max_rpm = machine.get("max_rpm", 0)
    if max_rpm >= 15000:
        if _is_solid_carbide_tool(record):
            delta += 1.0
        if _has_geometry_tag(record, "variable_helix", "high_helix", "multi_flute"):
            delta += 0.5
        if record.get("tool_category") == "milling_insert":
            delta -= 0.5
    elif max_rpm > 0 and max_rpm < 4000:
        if _is_indexable_insert(record):
            delta += 1.0
        if record.get("tool_category") == "endmill":
            delta -= 0.5

    tsc = machine.get("through_spindle_coolant")
    if tsc is False:
        if _coolant_is_through(record) and record.get("tool_category") in ("drill", "indexable_drill"):
            delta -= 1.5
    elif tsc is True:
        if _coolant_is_through(record) and record.get("tool_category") in ("drill", "indexable_drill"):
            delta += 1.5

    rigidity = machine.get("machine_rigidity", "")
    if rigidity == "low":
        if _has_geometry_tag(record, "variable_helix", "anti_vibration", "vibration_damped"):
            delta += 1.0
        if _is_high_feed(record):
            delta -= 1.0
    elif rigidity == "high":
        if _is_high_feed(record):
            delta += 0.5

    taper = machine.get("spindle_taper", "")
    if taper in ("BT30", "CAT30"):
        if _is_solid_carbide_tool(record):
            delta += 0.5
        if record.get("tool_category") in ("milling_insert", "indexable_drill"):
            delta -= 1.0

    size = machine.get("machine_size_class", "")
    if size == "small":
        if _is_solid_carbide_tool(record):
            delta += 0.5
        if record.get("tool_category") in ("milling_insert", "indexable_drill"):
            delta -= 0.5
    elif size == "heavy_duty":
        if _is_indexable_insert(record):
            delta += 0.5

    return delta


def score_setup_context(record: dict[str, Any], setup: dict[str, Any] | None) -> float:
    """Return boost/penalty delta based on setup context. Range: -2 to +2."""
    if not setup:
        return 0.0
    delta = 0.0

    stickout = setup.get("stickout_length", "")
    if stickout == "long":
        if _has_geometry_tag(record, "anti_vibration", "vibration_damped", "solid_carbide_shank"):
            delta += 1.0
        if _is_boring_bar(record):
            delta += 0.5
        if _has_geometry_tag(record, "seven_flute"):
            delta -= 0.5

    chatter = setup.get("chatter_risk", "")
    if chatter == "high":
        if _has_geometry_tag(record, "anti_vibration", "vibration_damped", "variable_helix"):
            delta += 1.5
        if _is_boring_bar(record):
            delta += 0.5
        if _has_geometry_tag(record, "five_flute", "seven_flute"):
            delta -= 0.5

    s_rig = setup.get("setup_rigidity", "")
    w_rig = setup.get("workholding_rigidity", "")
    worst = (
        "poor" if "poor" in (s_rig, w_rig)
        else ("average" if "average" in (s_rig, w_rig) else "")
    )
    if worst == "poor":
        if _is_high_feed(record):
            delta -= 1.0
        if _has_geometry_tag(record, "positive_rake", "light_cut"):
            delta += 0.5
        chipbreaker = str(record.get("chipbreaker", "")).upper()
        if any(cb in chipbreaker for cb in ("MR", "PR", "SM")):
            delta += 0.5

    holder = setup.get("holder_type", "")
    if holder in ("shrink_fit", "hydraulic"):
        if _is_solid_carbide_tool(record):
            delta += 0.5

    return delta


def score_production_context(record: dict[str, Any], production: dict[str, Any] | None) -> float:
    """Return boost/penalty delta based on production context. Range: -2 to +2."""
    if not production:
        return 0.0
    delta = 0.0

    pvp = production.get("prototype_vs_production", "")
    if pvp == "production":
        if _is_indexable_insert(record):
            delta += 1.0
        if _is_solid_carbide_tool(record):
            delta -= 0.3
    elif pvp == "prototype":
        if _is_solid_carbide_tool(record) and record.get("tool_category") in ("endmill", "drill"):
            delta += 1.0
        if record.get("tool_category") in ("turning_insert", "milling_insert"):
            delta -= 0.3

    tl = production.get("tool_life_priority", "")
    if tl == "high":
        if _coating_is_wear_resistant(record):
            delta += 1.0

    ct = production.get("cycle_time_priority", "")
    if ct == "high":
        if _is_high_feed(record):
            delta += 1.0
        elif record.get("tool_category") == "endmill" and _has_geometry_tag(
            record, "variable_helix", "multi_flute", "five_flute", "seven_flute"
        ):
            delta += 0.5

    cost = production.get("cost_priority", "")
    if cost == "high":
        if _is_indexable_insert(record):
            delta += 0.5
        if _is_solid_carbide_tool(record):
            delta -= 0.3

    rf = production.get("roughing_vs_finishing_priority", "")
    if rf == "roughing":
        if _is_high_feed(record):
            delta += 0.5
        chipbreaker = str(record.get("chipbreaker", "")).upper()
        if any(cb in chipbreaker for cb in ("MR", "PR", "MRR")):
            delta += 0.3
    elif rf == "finishing":
        chipbreaker = str(record.get("chipbreaker", "")).upper()
        if any(cb in chipbreaker for cb in ("PF", "MF", "WF", "XF")):
            delta += 0.3

    return delta


# ---------------------------------------------------------------------------
# Main scoring entry point
# ---------------------------------------------------------------------------

def score_context_boosts(record: dict[str, Any], ctx: dict[str, Any] | None) -> float:
    """Return the total context boost/penalty delta for a single tooling record.

    The returned delta is layered on top of the existing tooling_search match
    score — it never replaces or overrides the base scoring. When ctx is None
    or inactive, always returns 0.0 so existing behavior is unchanged.

    No cutting data, feeds, or speeds are read or used.
    """
    if not ctx or not context_is_active(ctx):
        return 0.0
    return (
        score_machine_context(record, ctx.get("machine"))
        + score_setup_context(record, ctx.get("setup"))
        + score_production_context(record, ctx.get("production"))
    )


# ---------------------------------------------------------------------------
# Candidate re-ranking
# ---------------------------------------------------------------------------

def apply_context_to_candidates(
    candidates: list[dict[str, Any]],
    ctx: dict[str, Any] | None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Re-rank an already-filtered candidate list using context boosts.

    The existing tooling_search scoring already produced `candidates` in
    match-score order. This function adds a small context delta and re-sorts,
    preserving the original relative ordering for equal-boost candidates.
    When context is inactive, candidates are returned unchanged.
    """
    if not candidates or not ctx or not context_is_active(ctx):
        return candidates[:limit] if limit else list(candidates)

    scored: list[tuple[float, int, dict[str, Any]]] = []
    for original_rank, record in enumerate(candidates):
        boost = score_context_boosts(record, ctx)
        scored.append((boost, original_rank, record))

    scored.sort(key=lambda x: (-x[0], x[1]))
    result = [record for _, _, record in scored]
    return result[:limit] if limit else result
