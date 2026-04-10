from .tooling_advisor import TOOL_FAMILY_LABELS


def get_tool_family_message(tool_family: str) -> dict:
    label = TOOL_FAMILY_LABELS[tool_family]
    if tool_family == "TURNING_INSERT":
        message = "Turning inserts use mapped grade behavior, insert identity output, and supplier-specific search terms built from coating, geometry, and chipbreaker direction."
    elif tool_family == "THREADING_INSERT":
        message = "Threading guidance uses the shared behavior engine plus thread profile and internal or external direction so the starter insert and catalog search stay thread-specific."
    elif tool_family in {"TAP", "REAMER"}:
        message = "This section uses the shared behavior engine plus hole-type input so the starter callout and supplier search reflect through-hole versus blind-hole work."
    else:
        message = f"{label} uses the shared material and setup behavior engine to return a shop-floor starter platform, setup guidance, and supplier search terms."
    return {
        "status": "LIVE",
        "title": f"{label} recommendations are active",
        "message": message,
    }
