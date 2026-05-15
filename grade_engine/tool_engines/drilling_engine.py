from __future__ import annotations

from typing import Any

from grade_engine.tool_engines.common import base_risk_flags, build_engine_output, build_layered_behavior


def resolve_drilling_engine(input_data: dict[str, Any]) -> dict[str, Any]:
    profile = build_layered_behavior(input_data, "Drilling engine")
    diameter_mm = float(input_data.get("diameter_mm", 12.0))
    l_d_ratio = int(input_data.get("l_d_ratio", 5))
    requested_type = input_data.get("drill_type")

    type_score = 0
    steps = list(profile["reasoning_steps"])
    risks = base_risk_flags(input_data)

    if diameter_mm >= 20.0:
        type_score += 2
        steps.append("Larger diameter pushes the direction toward indexable productivity.")
    elif diameter_mm <= 6.0:
        type_score -= 2
        steps.append("Smaller diameter pushes the direction toward solid-carbide accuracy.")
    else:
        steps.append("Mid-range diameter keeps both solid and indexable paths open.")

    if l_d_ratio >= 8:
        type_score -= 2
        steps.append("Higher L/D pushes toward solid-carbide reach and guidance.")
        risks.append("Deep hole ratio increases evacuation and straightness risk.")
    elif l_d_ratio >= 5:
        type_score -= 1
        steps.append("Moderate L/D still leans toward the more guided drill family.")
    else:
        type_score += 1
        steps.append("Shorter L/D allows a stronger push toward indexable productivity.")

    if profile["stability_level"] == "LOW":
        type_score -= 2
        steps.append("Low setup stability shifts the direction toward a more controlled solid drill path.")
        risks.append("Low setup stability may force lighter feed and closer breakthrough watch.")
    elif profile["stability_level"] == "MEDIUM":
        type_score -= 1
        steps.append("Medium stability keeps the recommendation conservative on drill body size.")

    if input_data["material_group"] in {"N", "S", "H"}:
        type_score -= 1
        steps.append("Material group nudges the choice toward solid-carbide geometry control.")
    elif input_data["material_group"] == "K":
        type_score += 1
        steps.append("Cast iron favors a stronger body and productivity-side drilling when size allows.")

    if input_data["finish_priority"] == "HIGH":
        type_score -= 1
        steps.append("Higher finish priority shifts toward the drill family with better size control.")
    if input_data["application_zone"] == "TOUGH":
        type_score += 1
        steps.append("Tough-zone drilling accepts a stronger productivity bias when the setup allows it.")
    elif input_data["application_zone"] == "WEAR":
        type_score -= 1
        steps.append("Wear-zone drilling stays conservative to protect consistency and tool life.")

    recommended_type = "Indexable Drill" if type_score >= 1 else "Solid Carbide Drill"
    if requested_type and requested_type != recommended_type:
        risks.append(f"Selected {requested_type.lower()} differs from the engine's first-choice direction.")

    coolant_preference = "Through-coolant preferred"
    if l_d_ratio <= 3 and input_data["material_group"] == "N":
        coolant_preference = "Coolant optional if chips stay open, but through-coolant is still preferred"
    elif l_d_ratio >= 8 or input_data["material_group"] in {"M", "S", "H"}:
        coolant_preference = "Through-coolant strongly preferred"

    if input_data["material_group"] == "N" and input_data["finish_priority"] == "HIGH":
        geometry_bias = "Sharper 130-135 degree point bias with freer cutting lips"
    elif input_data["application_zone"] == "TOUGH" or profile["stability_level"] != "HIGH" or input_data["material_group"] in {"P", "K", "H"}:
        geometry_bias = "Stronger 140-145 degree point bias with edge support"
    else:
        geometry_bias = "Balanced 135-140 degree point bias"

    tool_direction = (
        f"{recommended_type} starting direction for {diameter_mm:.1f} mm at {l_d_ratio}xD, "
        f"with {coolant_preference.lower()} and a {geometry_bias.lower()}."
    )

    summary = (
        f"Starts from a {recommended_type.lower()} bias using diameter, depth ratio, setup stability, "
        f"and {profile['material_text']} behavior to keep drilling practical for shop conditions."
    )
    if profile["stability_level"] != "HIGH":
        summary += " The setup is not fully stable, so keep breakout and chip evacuation under closer watch."

    return build_engine_output(
        tool_family=recommended_type,
        recommendation_title=f"{recommended_type} direction",
        recommendation_summary=summary,
        tool_direction=tool_direction,
        geometry_hint=geometry_bias,
        risk_flags=risks,
        reasoning_steps=steps,
        extras={
            "drill_type": recommended_type,
            "coolant_preference": coolant_preference,
            "geometry_bias": geometry_bias,
            "stability_bias": profile["stability_level"],
        },
    )
