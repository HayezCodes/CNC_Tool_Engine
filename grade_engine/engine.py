from collections import Counter
from .base_behavior import BASE_ZONE_BEHAVIOR
from .overlays import MATERIAL_GROUP_OVERLAY
from .modifiers import MODIFIER_RULES
from .insert_identity import build_insert_identity

SCORE_TO_LEVEL = {1:"LOW",2:"MEDIUM",3:"HIGH"}
TOUGHNESS_MEANING = {
    "HIGH":"Strong edge security for interruption, shock, and unstable setups",
    "MEDIUM":"Balanced edge strength and tool life for normal work",
    "LOW":"Sharper but less forgiving edge for stable finishing work",
}
WEAR_MEANING = {
    "HIGH":"Better heat resistance and longer life in stable, faster cuts",
    "MEDIUM":"General-purpose wear resistance",
    "LOW":"Less heat-focused, usually chosen to keep a stronger edge",
}
COATING_MEANING = {
    "CVD":"Leans toward heat resistance and wear life in stable conditions",
    "PVD":"Leans toward edge strength and toughness in unstable conditions",
}

def clamp_score(value:int)->int:
    return max(1,min(3,value))

def get_chipbreaker_hint(material_group:str, application_zone:str)->dict:
    if material_group == "P":
        mapping = {
            "TOUGH": ("MR / MRR style", "Heavier steel roughing usually wants a tougher breaker that keeps the edge supported."),
            "BALANCED": ("MR / MF style", "General steel work usually wants a middle-ground breaker that balances chip control and edge strength."),
            "WEAR": ("MF finishing style", "Stable finishing work usually benefits from a freer-cutting breaker with lower cutting forces."),
        }
        family, why = mapping[application_zone]
        return {"family": family, "why": why}
    if material_group == "M":
        mapping = {
            "TOUGH": ("SM roughing style", "Stainless roughing needs a breaker that stays positive but still supports the edge."),
            "BALANCED": ("SM general-purpose style", "General stainless work needs chip control without letting the insert rub."),
            "WEAR": ("SM finishing style", "Stainless finishing still needs a positive cutting action so the insert does not rub and work-harden the part."),
        }
        family, why = mapping[application_zone]
        return {"family": family, "why": why}
    generic = {
        "K":"Use a stable, wear-focused breaker that controls chips without over-lightening the edge.",
        "N":"Use a freer-cutting polished-style breaker with low cutting forces.",
        "S":"Use a positive but supported breaker that keeps heat and edge failure under control.",
        "H":"Use a stable wear-side breaker and avoid overly weak sharp geometries.",
    }
    return {"family":"General-purpose family","why":generic.get(material_group, "No chipbreaker hint available.")}

def get_geometry_hint(input_data:dict)->dict:
    application_zone = input_data["application_zone"]
    finish_priority = input_data["finish_priority"]
    doc_band = input_data["doc_band"]
    interrupted_cut = input_data["interrupted_cut"]
    workholding = input_data["workholding"]
    stickout = input_data["stickout"]

    unstable = interrupted_cut in ["LIGHT", "HEAVY"] or workholding in ["AVERAGE", "POOR"] or stickout == "LONG"
    rough_bias = application_zone == "TOUGH" or doc_band == "HEAVY" or interrupted_cut == "HEAVY"
    finish_bias = application_zone == "WEAR" or finish_priority == "HIGH" or doc_band == "LIGHT"

    if rough_bias or unstable:
        if interrupted_cut == "HEAVY" or workholding == "POOR":
            return {"geometry":"CNMG / stronger negative-turning direction","why":"Interrupted or less stable work usually benefits from a stronger shape with more edge support."}
        return {"geometry":"CNMG / DNMG supported-turning direction","why":"Moderately unstable or heavier work usually starts from a supported shape before moving sharper."}
    if finish_bias:
        return {"geometry":"VNMG / sharper finishing direction","why":"Stable lighter finishing work usually benefits from a sharper geometry that lowers cutting force."}
    return {"geometry":"DNMG as a broad starting point","why":"Balanced work can usually start with a versatile shape before narrowing into a more specialized geometry."}

def get_risk_flags(input_data:dict, preferred_coating:str, toughness_level:str, wear_level:str)->list:
    risks = []
    if input_data["interrupted_cut"] == "HEAVY":
        risks.append("High edge-chipping risk from interruption.")
    if input_data["workholding"] == "POOR":
        risks.append("Vibration risk from weak workholding.")
    if input_data["stickout"] == "LONG":
        risks.append("Deflection / chatter risk from long stickout.")
    if input_data["cutting_speed_band"] == "HIGH" and wear_level != "HIGH":
        risks.append("Speed may be too aggressive for the resolved wear level.")
    if input_data["application_zone"] == "WEAR" and preferred_coating == "PVD":
        risks.append("Wear-side cut resolved to PVD bias; watch tool life if the cut is very stable and hot.")
    if input_data["material_group"] == "M" and input_data["doc_band"] == "LIGHT":
        risks.append("Stainless finishing cut: avoid rubbing and keep feed honest.")
    return risks

def get_shop_language_steps(input_data:dict)->list:
    steps = []
    zone = input_data["application_zone"]
    if zone == "TOUGH":
        steps.append("TOUGH zone selected -> engine starts by protecting edge strength over wear life.")
    elif zone == "BALANCED":
        steps.append("BALANCED zone selected -> engine starts from a middle-ground grade behavior.")
    else:
        steps.append("WEAR zone selected -> engine starts by favoring heat resistance and tool life.")
    steps.append({
        "P":"P material group -> steel baseline behavior.",
        "M":"M material group -> stainless behavior adds toughness bias to fight heat and instability.",
        "K":"K material group -> cast iron pushes toward wear resistance.",
        "N":"N material group -> non-ferrous work usually allows freer cutting and wear-side bias.",
        "S":"S material group -> super alloys push both heat resistance and toughness upward.",
        "H":"H material group -> hardened work pushes strongly toward wear resistance.",
    }[input_data["material_group"]])
    if input_data["interrupted_cut"] == "LIGHT":
        steps.append("Light interruption -> slight move toward a tougher grade.")
    elif input_data["interrupted_cut"] == "HEAVY":
        steps.append("Heavy interruption -> strong move toward a tougher, less fragile grade.")
    if input_data["stickout"] == "LONG":
        steps.append("Long stickout -> more vibration risk, so the engine adds toughness.")
    if input_data["workholding"] == "AVERAGE":
        steps.append("Average workholding -> small shift toward toughness.")
    elif input_data["workholding"] == "POOR":
        steps.append("Poor workholding -> strong shift toward toughness because the setup is less stable.")
    if input_data["cutting_speed_band"] == "HIGH":
        steps.append("High speed -> more heat, so the engine pushes harder toward wear resistance.")
    elif input_data["cutting_speed_band"] == "LOW":
        steps.append("Low speed -> heat matters less, so wear resistance becomes less critical.")
    if input_data["doc_band"] == "LIGHT":
        steps.append("Light DOC -> more finishing-like behavior, so wear resistance gets extra weight.")
    elif input_data["doc_band"] == "HEAVY":
        steps.append("Heavy DOC -> stronger edge needed, so toughness gets extra weight.")
    if input_data["finish_priority"] == "HIGH":
        steps.append("Finish priority high -> engine adds weight toward wear resistance and size control.")
    return steps

def build_recommendation_summary(material_group:str, application_zone:str, toughness_level:str, wear_level:str, preferred_coating:str)->dict:
    material_labels = {"P":"steel","M":"stainless","K":"cast iron","N":"non-ferrous","S":"super alloy","H":"hardened"}
    material_text = material_labels.get(material_group, "material")
    if application_zone == "TOUGH":
        title = f"Tougher {material_text} starting grade"
        summary = "Best starting point when the cut is rougher, more interrupted, or less stable."
    elif application_zone == "BALANCED":
        title = f"Balanced {material_text} starting grade"
        summary = "Best starting point for normal shop work where you need a mix of edge strength and tool life."
    else:
        title = f"Wear-oriented {material_text} starting grade"
        summary = "Best starting point for stable work where heat resistance and longer life matter more."

    fit = []
    if toughness_level == "HIGH":
        fit.append("prioritizes edge security")
    elif toughness_level == "MEDIUM":
        fit.append("keeps balanced edge strength")
    else:
        fit.append("leans toward a freer-cutting edge")
    if wear_level == "HIGH":
        fit.append("pushes toward longer tool life")
    elif wear_level == "MEDIUM":
        fit.append("keeps wear life general-purpose")
    else:
        fit.append("does not over-prioritize wear resistance")
    fit.append(f"leans {preferred_coating} for coating strategy")

    return {"title":title,"summary":summary,"fit_sentence":"; ".join(fit).capitalize() + "."}

def resolve_grade_behavior(input_data:dict)->dict:
    base = BASE_ZONE_BEHAVIOR[input_data["application_zone"]]
    toughness = base["toughness"]
    wear = base["wear"]
    coating_votes = [base["preferred_coating"]]
    overlay = MATERIAL_GROUP_OVERLAY[input_data["material_group"]]
    toughness = clamp_score(toughness + overlay["toughness_bias"])
    wear = clamp_score(wear + overlay["wear_bias"])
    coating_votes.append(overlay["default_coating"])

    for field, value in input_data.items():
        if field in MODIFIER_RULES and value in MODIFIER_RULES[field]:
            rule = MODIFIER_RULES[field][value]
            toughness = clamp_score(toughness + rule["toughness"])
            wear = clamp_score(wear + rule["wear"])
            if rule["coating_bias"]:
                coating_votes.append(rule["coating_bias"])

    preferred_coating = Counter(coating_votes).most_common(1)[0][0]
    toughness_level = SCORE_TO_LEVEL[toughness]
    wear_level = SCORE_TO_LEVEL[wear]
    recommendation = build_recommendation_summary(input_data["material_group"], input_data["application_zone"], toughness_level, wear_level, preferred_coating)
    chipbreaker = get_chipbreaker_hint(input_data["material_group"], input_data["application_zone"])
    geometry = get_geometry_hint(input_data)
    insert_identity = build_insert_identity(input_data, geometry, chipbreaker)

    return {
        "material_group": input_data["material_group"],
        "application_zone": input_data["application_zone"],
        "required_toughness": toughness_level,
        "required_wear_resistance": wear_level,
        "preferred_coating": preferred_coating,
        "toughness_explained": TOUGHNESS_MEANING[toughness_level],
        "wear_explained": WEAR_MEANING[wear_level],
        "coating_explained": COATING_MEANING[preferred_coating],
        "grade_behavior_key": f"{input_data['material_group']}_{toughness_level}_T_{wear_level}_W_{preferred_coating}",
        "chipbreaker_hint": chipbreaker,
        "geometry_hint": geometry,
        "insert_identity": insert_identity,
        "risk_flags": get_risk_flags(input_data, preferred_coating, toughness_level, wear_level),
        "explanation_steps": get_shop_language_steps(input_data),
        "recommendation_title": recommendation["title"],
        "recommendation_summary": recommendation["summary"],
        "recommendation_fit_sentence": recommendation["fit_sentence"],
    }
