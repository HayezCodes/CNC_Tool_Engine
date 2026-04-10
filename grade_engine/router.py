from .tooling_advisor import TOOL_FAMILY_LABELS


def get_tool_family_message(tool_family: str) -> dict:
    label = TOOL_FAMILY_LABELS[tool_family]
    return {
        "status": "LIVE",
        "title": f"{label} recommendations are active",
        "message": f"{label} is wired into the shared material and setup behavior engine with supplier search output.",
    }
