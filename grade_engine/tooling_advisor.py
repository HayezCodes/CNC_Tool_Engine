from urllib.parse import quote_plus

from .engine import resolve_grade_behavior
from .overlays import MATERIAL_GROUP_OVERLAY
from .resolver import SUPPLIER_SEARCH, map_behavior_to_supplier_grades

TOOL_FAMILY_LABELS = {
    "TURNING_INSERT": "Turning Insert",
    "GROOVING_INSERT": "Grooving Insert",
    "THREADING_INSERT": "Threading Insert",
    "DRILL": "Drill",
    "ENDMILL": "Endmill",
    "FACE_MILL": "Face Mill",
    "TAP": "Tap",
    "REAMER": "Reamer",
}

MATERIAL_NAMES = {
    "P": "steel",
    "M": "stainless",
    "K": "cast iron",
    "N": "non-ferrous",
    "S": "super alloy",
    "H": "hardened steel",
}

SUPPLIERS = ("MSC", "SANDVIK", "KENNAMETAL", "ISCAR")

NON_TURNING_SUPPLIER_TOKENS = {
    "MSC": {
        "GROOVING_INSERT": "grooving insert",
        "THREADING_INSERT": "threading insert",
        "DRILL": "carbide drill",
        "ENDMILL": "carbide endmill",
        "FACE_MILL": "face mill",
        "TAP": "machine tap",
        "REAMER": "chucking reamer",
    },
    "SANDVIK": {
        "GROOVING_INSERT": "CoroCut grooving insert",
        "THREADING_INSERT": "laydown threading insert",
        "DRILL": "CoroDrill",
        "ENDMILL": "CoroMill end mill",
        "FACE_MILL": "CoroMill face mill",
        "TAP": "CoroTap",
        "REAMER": "reamer",
    },
    "KENNAMETAL": {
        "GROOVING_INSERT": "Top Notch grooving insert",
        "THREADING_INSERT": "laydown threading insert",
        "DRILL": "HPX drill",
        "ENDMILL": "Harvi end mill",
        "FACE_MILL": "face mill",
        "TAP": "machine tap",
        "REAMER": "reamer",
    },
    "ISCAR": {
        "GROOVING_INSERT": "Do-Grip grooving insert",
        "THREADING_INSERT": "laydown threading insert",
        "DRILL": "SumoCham drill",
        "ENDMILL": "end mill",
        "FACE_MILL": "face mill",
        "TAP": "machine tap",
        "REAMER": "reamer",
    },
}


def compact_tokens(*tokens: str) -> str:
    cleaned = []
    seen = set()
    for token in tokens:
        value = " ".join((token or "").split()).strip()
        if not value:
            continue
        key = value.upper()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(value)
    return " ".join(cleaned)


def get_stability_state(input_data: dict) -> str:
    instability = 0
    if input_data["interrupted_cut"] == "LIGHT":
        instability += 1
    elif input_data["interrupted_cut"] == "HEAVY":
        instability += 2
    if input_data["stickout"] == "LONG":
        instability += 1
    if input_data["workholding"] == "AVERAGE":
        instability += 1
    elif input_data["workholding"] == "POOR":
        instability += 2
    if instability >= 3:
        return "UNSTABLE"
    if instability >= 1:
        return "MIXED"
    return "STABLE"


def get_doc_text(doc_band: str) -> str:
    return {"LIGHT": "light", "MEDIUM": "medium", "HEAVY": "heavy"}[doc_band]


def get_tap_notes(material_group: str) -> tuple[list, list]:
    common_notes = [
        "Use spiral-point for through holes, spiral-flute for blind holes, and form taps only in ductile materials.",
        "Tap life is usually lost from poor hole size or alignment before coating becomes the main issue.",
    ]
    common_watch = [
        "Choose the chamfer style around the real hole type before ordering production taps.",
    ]

    if material_group == "N":
        return (
            common_notes
            + [
                "Form taps work well in ductile aluminum when the hole size and lube package are controlled.",
            ],
            common_watch
            + [
                "Do not force form taps into brittle non-ferrous castings or thin-wall parts.",
            ],
        )
    if material_group in {"M", "S"}:
        return (
            common_notes
            + [
                "Keep feed synchronized and use a sharp geometry so stainless and heat-resistant alloys do not work-harden ahead of the tap.",
            ],
            common_watch
            + [
                "Super alloy and stainless tapping need conservative first-pass speed and dependable lubricant delivery.",
            ],
        )
    return (
        common_notes
        + [
            "Rigid tapping still needs the correct chamfer count for the hole type.",
        ],
        common_watch
        + [
            "Do not treat form taps as a universal answer; chipless does not mean low torque.",
        ],
    )


def build_generic_supplier_query(tool_family: str, supplier: str, family_plan: dict) -> str:
    supplier_family_term = NON_TURNING_SUPPLIER_TOKENS.get(supplier, {}).get(tool_family, family_plan["supplier_seed"])
    return compact_tokens(supplier_family_term, *family_plan["search_terms"], family_plan["material_focus"])


def build_generic_supplier_matches(tool_family: str, result: dict, family_plan: dict) -> dict:
    matches = {}
    for supplier in SUPPLIERS:
        query = build_generic_supplier_query(tool_family, supplier, family_plan)
        search_url = SUPPLIER_SEARCH.get(supplier, "").format(query=quote_plus(query))
        matches[supplier] = {
            "recommended_grade": family_plan["starter_platform"],
            "fallback_grade": family_plan["fallback_platform"],
            "preferred_coating": result["preferred_coating"],
            "description": family_plan["catalog_description"],
            "search_query": query,
            "links": {"Search": search_url} if search_url else {},
        }
    return matches


def resolve_non_turning_family(tool_family: str, input_data: dict, behavior: dict) -> dict:
    material_name = MATERIAL_NAMES[input_data["material_group"]]
    stability = get_stability_state(input_data)
    doc_text = get_doc_text(input_data["doc_band"])
    finish_high = input_data["finish_priority"] == "HIGH"
    wear_high = behavior["required_wear_resistance"] == "HIGH"
    toughness_high = behavior["required_toughness"] == "HIGH"

    if tool_family == "GROOVING_INSERT":
        width = "2 mm" if finish_high or input_data["doc_band"] == "LIGHT" else "3 mm"
        starter = "neutral hand grooving / part-off blade"
        if toughness_high or stability != "STABLE":
            starter = "rigid double-ended grooving insert system"
        geometry = f"{width} width with supported edge"
        holder = "short overhang blade with the insert on spindle centerline"
        summary = f"Start with a {starter} for {doc_text} {material_name} work."
        notes = [
            "Use the narrowest blade that still clears the groove or cut-off width.",
            "Keep the blade extension as short as the part allows before increasing speed.",
            "If chips pack in the groove, widen slightly or add a freer-cutting chipformer.",
        ]
        watch = [
            "Blade overhang is the first place chatter starts in grooving.",
            "Part-off work gets unstable fast if coolant or chip evacuation falls behind.",
        ]
        supplier_seed = f"{width} grooving insert"
        search_terms = ["grooving insert", width, "parting", "cutoff", "supported edge"]
    elif tool_family == "THREADING_INSERT":
        starter = "partial-profile laydown threading insert"
        if finish_high and stability == "STABLE":
            starter = "full-profile laydown threading insert"
        geometry = "60 degree external laydown style"
        holder = "rigid laydown holder with minimum stickout and confirmed tip height"
        summary = f"Start with a {starter} in a {behavior['preferred_coating']} grade for {material_name} threads."
        notes = [
            "Partial-profile gives faster coverage across pitch changes; full-profile gives better crest control.",
            "Keep compound and infeed strategy consistent so the insert loads evenly.",
            "For gummy stainless or super alloy work, lean positive and keep the insert sharp.",
        ]
        watch = [
            "Threading punishes weak setup quickly, especially near shoulders.",
            "Check the nose style against the required root form before buying inserts.",
        ]
        supplier_seed = "threading insert laydown 60 degree"
        profile_style = "full profile" if "full-profile" in starter else "partial profile"
        search_terms = ["threading insert", "laydown", "60 degree", "external", profile_style]
    elif tool_family == "DRILL":
        series = "3xD stub drill" if stability != "STABLE" else "5xD carbide drill"
        if input_data["material_group"] == "N":
            starter = "polished aluminum drill"
            geometry = "130 degree polished point"
        elif input_data["material_group"] == "K":
            starter = f"through-coolant {series}"
            geometry = "140 degree strong-margin point"
        elif input_data["material_group"] == "H":
            starter = "solid carbide drill for hardened steel"
            geometry = "140 degree split point"
        else:
            starter = f"through-coolant {series}"
            geometry = "140 degree split point"
        holder = "short projection holder with runout checked at the drill margin"
        summary = f"Start with a {starter} matched to {doc_text} feed pressure and setup rigidity."
        notes = [
            "Shorter drills win first when the machine or setup is not rigid.",
            "Through-coolant matters most once chip evacuation becomes the limiting factor.",
            "If the cut squeals, reduce overhang before chasing coating changes.",
        ]
        watch = [
            "Long stickout and poor workholding usually show up as margin wear or drill walk first.",
            "Cast iron and hardened work need firm entry conditions; avoid rubbing starts.",
        ]
        supplier_seed = "carbide drill"
        drill_style = "polished aluminum" if input_data["material_group"] == "N" else "through coolant"
        search_terms = ["carbide drill", series, geometry, drill_style]
    elif tool_family == "ENDMILL":
        if input_data["material_group"] == "N":
            starter = "3 flute polished carbide endmill"
        elif input_data["material_group"] == "H":
            starter = "6 flute high-hard endmill"
        elif input_data["material_group"] in {"M", "S"}:
            starter = "5 flute variable-helix carbide endmill"
        else:
            starter = "4 flute variable-helix carbide endmill"
        geometry = "corner radius" if input_data["doc_band"] == "HEAVY" else "square end"
        holder = "shrink-fit or solid endmill holder with minimal gauge length"
        summary = f"Start with a {starter} and a {geometry} edge for {material_name} milling."
        notes = [
            "Match flute count to chip space before chasing more coating or speed.",
            "Variable helix is the safer first choice any time chatter is already on the table.",
            "For aluminum and copper alloys, polished flutes matter more than generic TiAlN claims.",
        ]
        watch = [
            "Heavy radial engagement and long stickout can break a good endmill recommendation fast.",
            "If finish matters, step down cutter wear before increasing feed per tooth.",
        ]
        supplier_seed = "carbide endmill"
        search_terms = ["carbide endmill", starter, geometry]
    elif tool_family == "FACE_MILL":
        starter = "45 degree positive face mill"
        if toughness_high or stability != "STABLE":
            starter = "positive lead-angle face mill with light entering force"
        geometry = "positive insert pocket" if input_data["material_group"] in {"M", "S"} else "general face-mill body"
        holder = "largest practical arbor or shell-mill mount the spindle will support"
        summary = f"Start with a {starter} to keep cutting forces manageable in {material_name} facemilling."
        notes = [
            "Positive cutters are the safer first move on lighter machines and weaker workholding.",
            "Keep cutter diameter just larger than the width of cut when possible.",
            "If edge failure shows up on entry, reduce engagement shock before changing grade.",
        ]
        watch = [
            "Interrupted milling plus weak workholding usually needs lighter radial engagement immediately.",
            "Do not oversize the face mill just because the machine can physically hold it.",
        ]
        supplier_seed = "face mill"
        search_terms = ["face mill", starter, geometry]
    elif tool_family == "TAP":
        if input_data["material_group"] == "N":
            starter = "form tap"
        elif input_data["material_group"] in {"M", "S"}:
            starter = "spiral-flute tap"
        else:
            starter = "spiral-point gun tap"
        geometry = "H-limit production style" if wear_high else "general-purpose thread limit"
        holder = "tension-compression or rigid synchronous holder with minimal runout"
        summary = f"Start with a {starter} and keep it simple on the first pass in {material_name}."
        notes, watch = get_tap_notes(input_data["material_group"])
        supplier_seed = "machine tap"
        hole_style = "blind hole" if starter == "spiral-flute tap" else "through hole"
        if starter == "form tap":
            hole_style = "ductile material"
        search_terms = ["machine tap", starter, geometry, hole_style]
    else:
        if input_data["material_group"] in {"H", "K"}:
            starter = "solid carbide chucking reamer"
        else:
            starter = "cobalt chucking reamer"
        geometry = "right-hand spiral" if input_data["material_group"] in {"M", "S"} else "straight flute"
        holder = "true-running holder or floating reamer holder after the hole is prepped straight"
        summary = f"Start with a {starter} in a {geometry} style for size control in {material_name}."
        notes = [
            "Reamers want a straight, clean pre-hole more than they want aggressive speed.",
            "Leave consistent stock before the reamer or the result will not repeat.",
            "If finish is poor, check the pre-hole and holder runout before blaming the reamer.",
        ]
        watch = [
            "Too little stock can rub and bellmouth the hole just as easily as too much stock can chatter.",
            "Blind-hole chips need a flute style that can actually evacuate them.",
        ]
        supplier_seed = "chucking reamer"
        search_terms = ["chucking reamer", starter, geometry]

    material_focus = MATERIAL_GROUP_OVERLAY[input_data["material_group"]]["label"]
    return {
        "family_label": TOOL_FAMILY_LABELS[tool_family],
        "recommendation_title": f"{TOOL_FAMILY_LABELS[tool_family]} starter for {material_name}",
        "recommendation_summary": summary,
        "recommendation_fit_sentence": behavior["recommendation_fit_sentence"],
        "starter_platform": starter,
        "fallback_platform": f"general-purpose {TOOL_FAMILY_LABELS[tool_family].lower()}",
        "geometry_focus": geometry,
        "holder_focus": holder,
        "catalog_description": f"{starter.capitalize()} with {geometry.lower()} guidance for {material_name} work.",
        "process_notes": notes,
        "watch_items": watch,
        "supplier_seed": supplier_seed,
        "search_terms": search_terms,
        "material_focus": material_focus,
    }


def resolve_tooling_recommendation(tool_family: str, input_data: dict) -> dict:
    behavior = resolve_grade_behavior(input_data)
    if tool_family == "TURNING_INSERT":
        supplier_matches = map_behavior_to_supplier_grades(
            behavior["material_group"],
            behavior["application_zone"],
            behavior["preferred_coating"],
            behavior["geometry_hint"],
            behavior["chipbreaker_hint"],
            behavior["insert_identity"],
        )
        return {
            "tool_family": tool_family,
            "family_label": TOOL_FAMILY_LABELS[tool_family],
            "behavior": behavior,
            "supplier_matches": supplier_matches,
            "starter_platform": behavior["insert_identity"]["identity_summary"],
            "geometry_focus": behavior["geometry_hint"]["geometry"],
            "holder_focus": "Use the most rigid holder and shortest stickout the part allows.",
            "process_notes": behavior["explanation_steps"],
            "watch_items": behavior["risk_flags"],
        }

    family_plan = resolve_non_turning_family(tool_family, input_data, behavior)
    supplier_matches = build_generic_supplier_matches(tool_family, behavior, family_plan)
    return {
        "tool_family": tool_family,
        "family_label": family_plan["family_label"],
        "behavior": {
            **behavior,
            "recommendation_title": family_plan["recommendation_title"],
            "recommendation_summary": family_plan["recommendation_summary"],
            "recommendation_fit_sentence": family_plan["recommendation_fit_sentence"],
        },
        "supplier_matches": supplier_matches,
        "starter_platform": family_plan["starter_platform"],
        "geometry_focus": family_plan["geometry_focus"],
        "holder_focus": family_plan["holder_focus"],
        "process_notes": behavior["explanation_steps"] + family_plan["process_notes"],
        "watch_items": behavior["risk_flags"] + family_plan["watch_items"],
    }
