ANSI_TO_ISO_SIZE = {
    "431": "150404",
    "432": "150408",
    "433": "150412",
}


def _choose_shape(application_zone: str, finish_priority: str, doc_band: str, interrupted_cut: str, workholding: str, geometry_hint: dict) -> str:
    geometry_text = (geometry_hint.get("geometry", "") if geometry_hint else "").upper()
    unstable = interrupted_cut in ["LIGHT", "HEAVY"] or workholding in ["AVERAGE", "POOR"]
    finish_bias = application_zone == "WEAR" or finish_priority == "HIGH" or doc_band == "LIGHT"
    rough_bias = application_zone == "TOUGH" or doc_band == "HEAVY" or interrupted_cut == "HEAVY"

    if "CNMG" in geometry_text and rough_bias:
        return "CNMG"
    if "VNMG" in geometry_text and finish_bias and not rough_bias:
        return "VNMG"

    if rough_bias or unstable:
        if interrupted_cut == "HEAVY" or workholding == "POOR":
            return "CNMG"
        return "DNMG"

    if finish_bias:
        return "VNMG"

    return "DNMG"


def _choose_ansi_size(application_zone: str, finish_priority: str, doc_band: str) -> str:
    if doc_band == "HEAVY" or application_zone == "TOUGH":
        return "433"
    if doc_band == "LIGHT" and (finish_priority == "HIGH" or application_zone == "WEAR"):
        return "431"
    return "432"


def _choose_nose_radius(application_zone: str, finish_priority: str, doc_band: str, interrupted_cut: str) -> str:
    if finish_priority == "HIGH" or doc_band == "LIGHT" or application_zone == "WEAR":
        return "small"
    if doc_band == "HEAVY" or application_zone == "TOUGH" or interrupted_cut == "HEAVY":
        return "large"
    return "medium"


def build_insert_identity(input_data: dict, geometry_hint: dict, chipbreaker_hint: dict) -> dict:
    application_zone = input_data.get("application_zone", "BALANCED")
    finish_priority = input_data.get("finish_priority", "NORMAL")
    doc_band = input_data.get("doc_band", "MEDIUM")
    interrupted_cut = input_data.get("interrupted_cut", "NONE")
    workholding = input_data.get("workholding", "GOOD")

    shape = _choose_shape(
        application_zone,
        finish_priority,
        doc_band,
        interrupted_cut,
        workholding,
        geometry_hint,
    )
    ansi_size = _choose_ansi_size(application_zone, finish_priority, doc_band)
    iso_size = ANSI_TO_ISO_SIZE.get(ansi_size, "150408")
    nose_radius = _choose_nose_radius(application_zone, finish_priority, doc_band, interrupted_cut)

    if application_zone == "TOUGH":
        mode = "roughing"
    elif application_zone == "WEAR":
        mode = "finishing"
    else:
        mode = "balanced"

    summary = f"{shape} {ansi_size} {nose_radius}-radius {mode} direction"

    return {
        "shape": shape,
        "ansi_size": ansi_size,
        "iso_size": iso_size,
        "nose_radius": nose_radius,
        "identity_summary": summary,
        "chipbreaker_family": (chipbreaker_hint or {}).get("family", "MR"),
        "future_shape_placeholders": ["WNMG", "SNMG"],
    }
