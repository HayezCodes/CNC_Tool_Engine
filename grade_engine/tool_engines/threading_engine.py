from __future__ import annotations

from typing import Any

from grade_engine.tool_engines.common import base_risk_flags, build_engine_output, build_layered_behavior


def resolve_threading_engine(input_data: dict[str, Any]) -> dict[str, Any]:
    profile = build_layered_behavior(input_data, "Threading engine")
    thread_type = str(input_data.get("thread_type", "external_threading"))
    pitch_hint = str(input_data.get("pitch_hint", "Medium"))
    steps = list(profile["reasoning_steps"])
    risks = base_risk_flags(input_data)

    internal = thread_type == "internal_threading"
    if internal:
        steps.append("Internal threading adds extra deflection and chip-clearance sensitivity.")
    else:
        steps.append("External threading allows a broader insert-family choice when stability is good.")

    if pitch_hint == "Fine":
        profile_direction = "partial profile"
        geometry_hint = "Finer-pitch threading direction with lighter-force control"
        steps.append("Fine pitch pushes the starting point toward a more flexible partial-profile direction.")
    elif pitch_hint == "Coarse":
        profile_direction = "laydown"
        geometry_hint = "Coarser-pitch laydown direction with stronger flank support"
        steps.append("Coarser pitch supports a stronger laydown-style threading path.")
    elif internal or profile["stability_level"] != "HIGH":
        profile_direction = "laydown"
        geometry_hint = "Stable laydown direction to protect insert position and flank support"
        steps.append("Stability-sensitive threading stays with a stronger laydown direction.")
    else:
        profile_direction = "partial profile"
        geometry_hint = "General-purpose partial-profile direction for flexible pitch coverage"
        steps.append("Stable general threading can start from a flexible partial-profile direction.")

    if internal and input_data["stickout"] == "LONG":
        risks.append("Internal reach plus long stickout raises chatter and flank accuracy risk.")
    if input_data["material_group"] in {"M", "S"}:
        risks.append("Heat and chip packing can raise insert wear in threading.")

    tool_direction = (
        f"{profile_direction.title()} threading direction for "
        f"{'internal' if internal else 'external'} work with a {pitch_hint.lower()} pitch bias."
    )
    summary = (
        f"Starts from thread access, pitch sensitivity, and setup stability to decide between laydown and "
        f"partial-profile threading direction."
    )

    return build_engine_output(
        tool_family="Threading Insert",
        recommendation_title=f"{profile_direction.title()} threading direction",
        recommendation_summary=summary,
        tool_direction=tool_direction,
        geometry_hint=geometry_hint,
        risk_flags=risks,
        reasoning_steps=steps,
        extras={
            "thread_profile_direction": profile_direction,
            "thread_access": "internal" if internal else "external",
            "pitch_hint": pitch_hint,
        },
    )
