from __future__ import annotations

from typing import Any

from grade_engine.tool_engines.common import base_risk_flags, build_engine_output, build_layered_behavior


def resolve_grooving_engine(input_data: dict[str, Any]) -> dict[str, Any]:
    profile = build_layered_behavior(input_data, "Grooving engine")
    operation = str(input_data.get("operation", "Grooving"))
    steps = list(profile["reasoning_steps"])
    risks = base_risk_flags(input_data)

    operation_map = {
        "Grooving": "grooving",
        "Parting": "parting",
        "Face Grooving": "face_grooving",
        "Undercutting": "undercutting",
    }
    operation_key = operation_map.get(operation, "grooving")

    if operation_key == "parting":
        blade_rigidity = "highest blade rigidity direction"
        geometry_hint = "Narrow, well-supported parting system with steady chip control"
        steps.append("Parting demands the strongest blade support and clean chip control.")
    elif operation_key == "face_grooving":
        blade_rigidity = "face-groove holder direction"
        geometry_hint = "Face-entry geometry that protects side clearance and chip roll-out"
        steps.append("Face grooving pushes the holder direction toward better side-entry clearance.")
    elif operation_key == "undercutting":
        blade_rigidity = "rigid reach-controlled undercutting direction"
        geometry_hint = "Reach-aware undercutting geometry with chip escape emphasis"
        steps.append("Undercutting keeps the path focused on reach and chip escape.")
    else:
        blade_rigidity = "general grooving rigidity direction"
        geometry_hint = "Balanced grooving geometry with stable blade support"
        steps.append("Standard grooving keeps the direction on a balanced blade system.")

    if profile["stability_level"] != "HIGH":
        risks.append("Grooving stability is limited, so blade overhang and feed shock need extra caution.")
        steps.append("Lower setup stability adds extra bias toward a stiffer blade path.")

    if input_data["material_group"] in {"M", "S"}:
        risks.append("Stringier chip behavior may require closer chip evacuation control.")
        steps.append("Material family adds chip-control pressure to the grooving choice.")

    tool_direction = (
        f"{operation.replace('_', ' ')} direction with {blade_rigidity.lower()} and "
        f"{geometry_hint.lower()}."
    )
    summary = (
        f"Starts from operation type, setup stability, and material chip behavior to steer the groove system "
        f"toward the right blade style and evacuation bias."
    )

    return build_engine_output(
        tool_family="Grooving Insert",
        recommendation_title=f"{operation} direction",
        recommendation_summary=summary,
        tool_direction=tool_direction,
        geometry_hint=geometry_hint,
        risk_flags=risks,
        reasoning_steps=steps,
        extras={
            "operation_type": operation_key,
            "blade_rigidity": blade_rigidity,
            "chip_evacuating_priority": "HIGH" if input_data["material_group"] in {"M", "S"} or operation_key == "parting" else "MEDIUM",
        },
    )
