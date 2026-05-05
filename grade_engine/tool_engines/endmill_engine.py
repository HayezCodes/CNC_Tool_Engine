from __future__ import annotations

from typing import Any

from grade_engine.tool_engines.common import base_risk_flags, build_engine_output, build_layered_behavior


def resolve_endmill_engine(input_data: dict[str, Any]) -> dict[str, Any]:
    profile = build_layered_behavior(input_data, "Endmill engine")
    strategy = str(input_data.get("operation", "Profiling"))
    steps = list(profile["reasoning_steps"])
    risks = base_risk_flags(input_data)

    if strategy == "High Velocity" or input_data["material_group"] == "N":
        strategy_bias = "high_velocity"
        flute_count_direction = "2-3 flute freer-gullet direction"
        geometry_hint = "Sharper rake and freer chip space for lighter radial engagement"
        steps.append("Strategy and material point toward a high-velocity aluminum-style endmill path.")
    elif strategy == "Finishing" or input_data["finish_priority"] == "HIGH" or input_data["application_zone"] == "WEAR":
        strategy_bias = "finishing"
        flute_count_direction = "4-6 flute finishing direction"
        geometry_hint = "Tighter pitch and finish-side edge support"
        steps.append("Finish-side conditions push toward a denser flute package and steadier finishing path.")
    elif strategy == "Roughing" or input_data["doc_band"] == "HEAVY" or input_data["application_zone"] == "TOUGH":
        strategy_bias = "roughing"
        flute_count_direction = "3-4 flute roughing/general-purpose direction"
        geometry_hint = "Stronger core and chip-clearance bias for heavier engagement"
        steps.append("Heavier engagement shifts the path toward roughing or general-purpose endmills.")
    else:
        strategy_bias = "general"
        flute_count_direction = "4 flute general-purpose direction"
        geometry_hint = "Balanced core strength and chip room"
        steps.append("Balanced conditions keep the recommendation on a general-purpose endmill path.")

    chatter_risk = input_data["stickout"] == "LONG" or input_data["workholding"] != "GOOD"
    if chatter_risk:
        risks.append("Chatter risk is elevated, so avoid overly light, weak flute packages.")
        steps.append("Setup stability pushes the endmill path toward stronger core support.")

    tool_direction = (
        f"{strategy_bias.replace('_', ' ').title()} endmill direction with a "
        f"{flute_count_direction.lower()} and {geometry_hint.lower()}."
    )
    summary = (
        f"Starts from a {strategy_bias.replace('_', ' ')} endmill bias using zone, material behavior, "
        f"finish priority, and stability to steer flute count and chip-room direction."
    )

    return build_engine_output(
        tool_family="Endmill",
        recommendation_title=f"{strategy_bias.replace('_', ' ').title()} endmill direction",
        recommendation_summary=summary,
        tool_direction=tool_direction,
        geometry_hint=geometry_hint,
        risk_flags=risks,
        reasoning_steps=steps,
        extras={
            "strategy_bias": strategy_bias,
            "flute_count_direction": flute_count_direction,
            "chatter_risk": "HIGH" if chatter_risk else "LOW",
        },
    )
