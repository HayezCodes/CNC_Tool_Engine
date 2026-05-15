from __future__ import annotations

from typing import Any

from grade_engine.tool_engines.common import base_risk_flags, build_engine_output, build_layered_behavior


def resolve_facemill_engine(input_data: dict[str, Any]) -> dict[str, Any]:
    profile = build_layered_behavior(input_data, "Face mill engine")
    operation = str(input_data.get("operation", "Facing"))
    steps = list(profile["reasoning_steps"])
    risks = base_risk_flags(input_data)

    if operation == "Plunge Milling" or input_data["application_zone"] == "TOUGH":
        cutter_style = "high_feed"
        insert_density = "moderate insert density"
        geometry_hint = "Strong entering-angle, feed-forward cutter path"
        steps.append("Plunge or tough-side work pushes toward a high-feed cutter direction.")
    elif operation == "Shoulder Milling" or input_data["doc_band"] == "HEAVY":
        cutter_style = "shoulder"
        insert_density = "lower insert density with stronger edge access"
        geometry_hint = "Shoulder-capable geometry with stronger edge support"
        steps.append("Shoulder work and heavier DOC bias the recommendation toward stronger shoulder tools.")
    else:
        cutter_style = "face"
        insert_density = "higher insert density for smoother face passes"
        geometry_hint = "Face-milling geometry tuned for smoother cutter engagement"
        steps.append("Balanced face work keeps the direction on a true face-mill path.")

    if profile["stability_level"] != "HIGH":
        insert_density = "moderate insert density to control entry shock"
        risks.append("Setup stability favors fewer hard-entering edges at once.")
        steps.append("Stability risk trims insert density to keep cutter entry calmer.")

    if input_data["cutting_speed_band"] == "HIGH" and cutter_style == "face":
        steps.append("Higher speed band supports a denser face-mill path when stability allows.")
    if input_data["finish_priority"] == "HIGH":
        steps.append("Finish priority keeps the direction closer to a smoother face-milling path.")

    tool_direction = (
        f"{cutter_style.replace('_', ' ').title()} cutter direction with {insert_density.lower()} "
        f"and {geometry_hint.lower()}."
    )
    summary = (
        f"Starts from operation intent, DOC, finish priority, and setup stability to decide between "
        f"high-feed, shoulder, and true face-milling behavior."
    )

    return build_engine_output(
        tool_family="Face Mill",
        recommendation_title=f"{cutter_style.replace('_', ' ').title()} cutter direction",
        recommendation_summary=summary,
        tool_direction=tool_direction,
        geometry_hint=geometry_hint,
        risk_flags=risks,
        reasoning_steps=steps,
        extras={
            "cutter_style": cutter_style,
            "insert_density": insert_density,
        },
    )
