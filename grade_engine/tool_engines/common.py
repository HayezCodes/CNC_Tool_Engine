from __future__ import annotations

from collections import Counter
from typing import Any

from grade_engine.base_behavior import BASE_ZONE_BEHAVIOR
from grade_engine.modifiers import MODIFIER_RULES
from grade_engine.overlays import MATERIAL_GROUP_OVERLAY

SCORE_TO_LEVEL = {1: "LOW", 2: "MEDIUM", 3: "HIGH"}
MATERIAL_TEXT = {
    "P": "steel",
    "M": "stainless",
    "K": "cast iron",
    "N": "non-ferrous",
    "S": "super alloy",
    "H": "hardened",
}


def clamp_score(value: int) -> int:
    return max(1, min(3, value))


def stability_level(input_data: dict[str, Any]) -> str:
    penalty = 0
    if input_data["interrupted_cut"] == "HEAVY":
        penalty += 2
    elif input_data["interrupted_cut"] == "LIGHT":
        penalty += 1
    if input_data["stickout"] == "LONG":
        penalty += 1
    if input_data["workholding"] == "POOR":
        penalty += 2
    elif input_data["workholding"] == "AVERAGE":
        penalty += 1

    if penalty >= 3:
        return "LOW"
    if penalty >= 1:
        return "MEDIUM"
    return "HIGH"


def build_layered_behavior(input_data: dict[str, Any], tool_name: str) -> dict[str, Any]:
    base = BASE_ZONE_BEHAVIOR[input_data["application_zone"]]
    overlay = MATERIAL_GROUP_OVERLAY[input_data["material_group"]]
    toughness = clamp_score(base["toughness"] + overlay["toughness_bias"])
    wear = clamp_score(base["wear"] + overlay["wear_bias"])
    coating_votes = [base["preferred_coating"], overlay["default_coating"]]

    steps = [
        f"{tool_name}: {input_data['application_zone']} zone sets the starting balance.",
        f"{input_data['material_group']} material overlay shifts the baseline for {MATERIAL_TEXT[input_data['material_group']]}.",
    ]

    for field, value in input_data.items():
        if field in MODIFIER_RULES and value in MODIFIER_RULES[field]:
            rule = MODIFIER_RULES[field][value]
            toughness = clamp_score(toughness + rule["toughness"])
            wear = clamp_score(wear + rule["wear"])
            if rule["coating_bias"]:
                coating_votes.append(rule["coating_bias"])
            steps.append(
                f"{field.replace('_', ' ')}={value.lower()} modifies the balance toward "
                f"{'toughness' if rule['toughness'] > 0 else 'wear' if rule['wear'] > 0 else 'stability'}."
            )

    preferred_coating = Counter(coating_votes).most_common(1)[0][0]
    return {
        "toughness_score": toughness,
        "wear_score": wear,
        "required_toughness": SCORE_TO_LEVEL[toughness],
        "required_wear_resistance": SCORE_TO_LEVEL[wear],
        "preferred_coating": preferred_coating,
        "material_text": MATERIAL_TEXT[input_data["material_group"]],
        "stability_level": stability_level(input_data),
        "reasoning_steps": steps,
    }


def base_risk_flags(input_data: dict[str, Any]) -> list[str]:
    risks: list[str] = []
    if input_data["interrupted_cut"] == "HEAVY":
        risks.append("Heavy interruption raises edge security and vibration risk.")
    if input_data["workholding"] == "POOR":
        risks.append("Poor workholding raises chatter and tool-life risk.")
    if input_data["stickout"] == "LONG":
        risks.append("Long stickout increases deflection risk.")
    if input_data["cutting_speed_band"] == "HIGH":
        risks.append("High speed band will raise heat sensitivity.")
    return risks


def build_engine_output(
    *,
    tool_family: str,
    recommendation_title: str,
    recommendation_summary: str,
    tool_direction: str,
    geometry_hint: str,
    risk_flags: list[str],
    reasoning_steps: list[str],
    extras: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result = {
        "tool_family": tool_family,
        "recommendation_title": recommendation_title,
        "recommendation_summary": recommendation_summary,
        "tool_direction": tool_direction,
        "geometry_hint": geometry_hint,
        "risk_flags": risk_flags,
        "reasoning_steps": reasoning_steps,
    }
    if extras:
        result.update(extras)
    return result
