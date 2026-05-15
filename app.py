import inspect
import json
from numbers import Real
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
import streamlit as st

from grade_engine.brand_intelligence import (
    infer_brand_intelligence_from_query,
    load_brand_intelligence,
    recommend_brand_families,
)
from grade_engine.catalog_review import (
    filter_reviewed_catalog_records,
    get_reviewed_catalog_summary,
)
from grade_engine.engine import resolve_grade_behavior
from grade_engine.enums import (
    APPLICATION_ZONES,
    CUTTING_SPEED_BAND,
    DOC_BAND,
    FINISH_PRIORITY,
    INTERRUPTED_CUT,
    MATERIAL_GROUPS,
    STICKOUT,
    WORKHOLDING,
)
from grade_engine.tool_engines import (
    resolve_drilling_engine,
    resolve_endmill_engine,
    resolve_facemill_engine,
    resolve_grooving_engine,
    resolve_threading_engine,
)
from grade_engine.problem_solver import solve_operation_problem
from grade_engine.tooling_search import (
    explain_tool_match,
    load_tooling_records,
    normalize_tool_query,
    search_tooling_records,
    suggest_tool_candidates,
)
from tool_lookup.cross_reference import cross_reference_tool
from tool_lookup.index import load_lookup_records

MATERIAL_GROUP_LABELS = {
    "P": "P — Steel",
    "M": "M — Stainless",
    "K": "K — Cast Iron",
    "N": "N — Non-Ferrous",
    "S": "S — Super Alloy",
    "H": "H — Hardened",
}

FAMILY_LABELS = {
    "TURNING_INSERT": "Turning",
    "DRILL": "Drilling",
    "ENDMILL": "Endmill",
    "FACE_MILL": "Face Mill",
    "GROOVING_INSERT": "Grooving / Parting",
    "THREADING_INSERT": "Threading",
    "BURNISHING": "Burnishing",
    "WORKHOLDING": "Workholding",
    "TOOL_LOOKUP": "Tool Lookup / Cross Reference",
    "BRAND_INTELLIGENCE": "Brand Intelligence",
}

DATA_ROOT = Path(__file__).parent / "tool_data"

MODULE_DESCRIPTIONS = {
    "TURNING_INSERT": "Starting-point insert family and grade guidance for common turning conditions.",
    "DRILL": "Holemaking family shortlist based on diameter, depth ratio, material, and setup intent.",
    "ENDMILL": "Solid endmill family guidance tuned to strategy, material group, and finish goals.",
    "FACE_MILL": "Indexable cutter shortlist for facing, shoulder work, and plunge-capable milling families.",
    "GROOVING_INSERT": "Family-level grooving and parting guidance with grade support tied to the selected ISO group.",
    "THREADING_INSERT": "Threading family shortlist with material- and zone-aware grade support.",
    "BURNISHING": "Reference screen for finish-improvement tools when size, finish, and surface integrity matter.",
    "WORKHOLDING": "Reference screen for chucking and setup stability options that support the cutting recommendation.",
    "TOOL_LOOKUP": "Cross-reference manufacturer numbers, designation families, and series names without relying on fragile product links.",
    "BRAND_INTELLIGENCE": "Family-level brand and tool-family guidance by operation, material group, and shop priority.",
}

DRILL_TYPE_HINTS = {
    "Solid Carbide Drill": "Best when size control, reach, and smaller-diameter hole quality matter most.",
    "Indexable Drill": "Best when diameter is larger and the holemaking priority leans toward productivity and insert economy.",
}

TURNING_INTENTS = ["Roughing", "Medium / General", "Finishing"]
ENGINE_VERIFICATION_NOTE = (
    "Family-level planning guidance only. Verify exact tool geometry, size, and cutting data with the "
    "manufacturer catalog and your machine setup."
)


def load_json(relative_path: str) -> Any:
    path = DATA_ROOT / relative_path
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def flatten_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple, set)):
        out: list[str] = []
        for item in value:
            out.extend(flatten_list(item))
        return out
    return [str(value)]


def has_iso_group(record: dict[str, Any], iso_group: str) -> bool:
    candidates: list[str] = []
    for path in [
        ["materials", "iso_groups"],
        ["materials", "preferred_groups"],
        ["primary_iso_group"],
    ]:
        current: Any = record
        ok = True
        for key in path:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                ok = False
                break
        if ok:
            candidates.extend(flatten_list(current))
    return iso_group in candidates if candidates else True


def text_blob(record: dict[str, Any]) -> str:
    parts: list[str] = []

    def walk(obj: Any) -> None:
        if isinstance(obj, dict):
            for value in obj.values():
                walk(value)
        elif isinstance(obj, (list, tuple, set)):
            for value in obj:
                walk(value)
        elif obj is not None:
            parts.append(str(obj).lower())

    walk(record)
    return " ".join(parts)


def match_terms(blob: str, terms: Iterable[str]) -> int:
    score = 0
    for term in terms:
        if term and term.lower() in blob:
            score += 1
    return score


def titleize_token(value: str) -> str:
    return value.replace("_", " ").title()


def clean_text(value: str) -> str:
    if not isinstance(value, str):
        return value
    return (
        value
        .encode("ascii", "ignore")
        .decode()
        .replace("  ", " ")
        .strip()
    )


def display_text(value: Any) -> str:
    if value in (None, "", [], {}):
        return "Not listed"
    if isinstance(value, list):
        cleaned = [display_text(item) for item in value if item not in (None, "", [], {})]
        return ", ".join(item for item in cleaned if item != "Not listed") or "Not listed"
    if isinstance(value, dict):
        return format_mapping(value)
    return clean_text(str(value))


def compact_list(values: Iterable[Any]) -> str:
    items = [clean_text(str(value)) for value in values if value not in (None, "", [], {})]
    return ", ".join(items) if items else "Not listed"


def format_mapping(mapping: dict[str, Any]) -> str:
    if not mapping:
        return "Not listed"
    return "; ".join(
        f"{titleize_token(clean_text(str(key)))}: {display_text(value)}"
        for key, value in mapping.items()
    )


def preferred_frame(rows: list[dict[str, Any]], preferred_columns: list[str]) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    columns = [column for column in preferred_columns if column in frame.columns]
    return frame[columns] if columns else frame


def build_turning_intent_profile(common: dict[str, Any], turning_intent: str) -> dict[str, Any]:
    profile = {
        "intent": turning_intent,
        "chipbreaker_weights": {},
        "primary_chipbreakers": [],
        "secondary_chipbreakers": [],
        "keyword_terms": [],
        "edge_direction": "Balanced edge direction.",
        "nose_radius_direction": "Moderate nose radius direction.",
        "intent_caption": "General-purpose turning bias.",
        "shop_preference": None,
    }

    if turning_intent == "Roughing":
        profile.update(
            {
                "chipbreaker_weights": {"PR": 3, "MR": 2, "MRR": 3, "MF": 1, "SM": 1},
                "primary_chipbreakers": ["PR", "MR", "MRR"],
                "secondary_chipbreakers": ["MF", "SM"],
                "keyword_terms": ["rough", "heavy", "medium", "general"],
                "edge_direction": "Stronger edge / roughing direction.",
                "nose_radius_direction": "Larger nose radius direction when setup and feature size allow.",
                "intent_caption": "Bias toward stronger-edge, roughing-capable families.",
            }
        )
    elif turning_intent == "Finishing":
        profile.update(
            {
                "chipbreaker_weights": {"PF": 3, "MF": 2, "WF": 2, "XF": 2, "FINISHING": 2, "MR": 1},
                "primary_chipbreakers": ["PF", "MF"],
                "secondary_chipbreakers": ["WF", "XF", "FINISHING", "MR"],
                "keyword_terms": ["finish", "wiper", "light", "profil", "precision"],
                "edge_direction": "Sharper, lower-force finishing direction.",
                "nose_radius_direction": "Smaller nose radius direction when print and edge strength permit.",
                "intent_caption": "Bias toward lower-force, finishing-oriented families.",
            }
        )
    else:
        profile.update(
            {
                "chipbreaker_weights": {"MR": 2, "MF": 2, "PF": 1, "PR": 1},
                "primary_chipbreakers": ["MR", "MF"],
                "secondary_chipbreakers": ["PF", "PR"],
                "keyword_terms": ["medium", "general", "balanced", "turning"],
                "edge_direction": "Balanced edge / medium-cut direction.",
                "nose_radius_direction": "Moderate nose radius direction for general turning.",
                "intent_caption": "Bias toward medium-cut, general-purpose families.",
            }
        )

    if common.get("material_group") == "P":
        chipbreaker_weights = dict(profile["chipbreaker_weights"])
        if turning_intent == "Roughing" or common.get("doc_band") == "HEAVY":
            chipbreaker_weights["PR"] = max(chipbreaker_weights.get("PR", 0), 5)
            chipbreaker_weights["MR"] = max(chipbreaker_weights.get("MR", 0), 2)
            chipbreaker_weights["MF"] = max(chipbreaker_weights.get("MF", 0), 1)
            profile["shop_preference"] = "PR"
        elif turning_intent == "Finishing" or common.get("finish_priority") == "HIGH":
            chipbreaker_weights["PF"] = max(chipbreaker_weights.get("PF", 0), 5)
            chipbreaker_weights["MF"] = max(chipbreaker_weights.get("MF", 0), 2)
            chipbreaker_weights["MR"] = max(chipbreaker_weights.get("MR", 0), 1)
            profile["shop_preference"] = "PF"
        profile["chipbreaker_weights"] = chipbreaker_weights

    return profile


def dataframe_display_kwargs(height: int | None = None) -> dict[str, Any]:
    kwargs: dict[str, Any] = {}
    if height is not None:
        kwargs["height"] = height
    if "width" in inspect.signature(st.dataframe).parameters:
        kwargs["width"] = "stretch"
    else:
        kwargs["use_container_width"] = True
    return kwargs


def render_empty_state(module_label: str, material_group: str, note: str | None = None) -> None:
    material_label = MATERIAL_GROUP_LABELS.get(material_group, material_group)
    st.warning(f"No {module_label.lower()} matches are available in the current demo dataset for {material_label}.")
    if note:
        st.caption(note)


def extract_short_sentence(text: str) -> str:
    cleaned = clean_text(text or "")
    if not cleaned:
        return "Not listed."
    for separator in [". ", "; ", " | "]:
        if separator in cleaned:
            first = cleaned.split(separator, 1)[0].strip()
            if first and first[-1] not in ".!?":
                first += "."
            return first
    if cleaned[-1] not in ".!?":
        cleaned += "."
    return cleaned


def format_reason_text(reasons: list[str], limit: int = 3) -> str:
    trimmed = [clean_text(reason) for reason in reasons if reason][:limit]
    return " | ".join(trimmed) if trimmed else "Family aligns with the selected planning direction."


def render_verification_note(note: str = ENGINE_VERIFICATION_NOTE) -> None:
    st.caption("Verification note: " + clean_text(note))


def render_reviewed_catalog_support(record: dict[str, Any], expanded: bool = False) -> None:
    support = record.get("reviewed_catalog_support")
    if not support:
        return
    with st.expander("Reviewed Catalog Support", expanded=expanded):
        if support.get("supporting_families"):
            st.write("Supporting families: " + compact_list(support["supporting_families"]))
        if support.get("matched_reasons"):
            st.write("Matched reasons: " + compact_list(support["matched_reasons"]))
        if support.get("confidence_level"):
            st.write("Confidence level: " + clean_text(support["confidence_level"]))
        render_verification_note(support.get("verification_note", ENGINE_VERIFICATION_NOTE))


def render_family_recommendation_card(
    *,
    header: str,
    direction: str,
    family_value: str,
    why_this_fits: str,
    risks: list[str] | None = None,
    summary: str | None = None,
    family_label: str = "Suggested tool/insert family",
    reviewed_support_record: dict[str, Any] | None = None,
    source_lines: list[str] | None = None,
    raw_scoring_lines: list[str] | None = None,
    verification_note: str = ENGINE_VERIFICATION_NOTE,
) -> None:
    with st.container(border=True):
        st.markdown(f"#### {clean_text(header)}")
        if summary:
            st.write(clean_text(summary))
        st.write(f"**Recommended direction:** {clean_text(direction)}")
        st.write(f"**{clean_text(family_label)}:** {clean_text(family_value)}")
        st.write(f"**Why this fits:** {clean_text(why_this_fits)}")
        if risks:
            st.warning("Risks / cautions: " + " | ".join(clean_text(risk) for risk in risks))
        if reviewed_support_record:
            render_reviewed_catalog_support(reviewed_support_record)
        if source_lines:
            with st.expander("Source/details"):
                for line in source_lines:
                    st.write(clean_text(line))
        if raw_scoring_lines:
            with st.expander("Raw scoring details"):
                for line in raw_scoring_lines:
                    st.write(clean_text(line))
        render_verification_note(verification_note)


def render_engine_basis(common: dict[str, Any], behavior: dict[str, Any]) -> None:
    render_metric_strip(
        [
            ("Zone", common["application_zone"]),
            ("Toughness Bias", behavior["required_toughness"]),
            ("Wear Bias", behavior["required_wear_resistance"]),
            ("Coating Dir.", clean_text(behavior["preferred_coating"])),
            ("Geometry / Chipbreaker", clean_text(behavior["chipbreaker_hint"]["family"])),
        ]
    )
    st.write(extract_short_sentence(behavior["recommendation_summary"]))
    with st.expander("Source/details"):
        st.write("Geometry direction: " + display_text(behavior.get("geometry_hint")))
        st.write("Starting identity: " + display_text(behavior.get("insert_identity", {}).get("identity_summary")))
        if behavior["risk_flags"]:
            st.write("Setup watch-outs: " + " | ".join(clean_text(flag) for flag in behavior["risk_flags"]))
    render_verification_note()


def render_tool_engine_result(result: dict[str, Any], metrics: list[tuple[str, str]]) -> None:
    with st.container(border=True):
        st.markdown(f"### {clean_text(result['recommendation_title'])}")
        st.write(clean_text(result["recommendation_summary"]))
        st.write(f"**Recommended direction:** {clean_text(result.get('tool_direction', result['recommendation_title']))}")
        if result.get("recommendation_fit_sentence"):
            st.write(f"**Why this fits:** {clean_text(result['recommendation_fit_sentence'])}")
        render_metric_strip([(clean_text(label), clean_text(value)) for label, value in metrics])
        if result["risk_flags"]:
            st.warning("Risks / cautions: " + " | ".join(clean_text(flag) for flag in result["risk_flags"]))
        render_verification_note()
        with st.expander("Source/details"):
            st.write("Geometry / chipbreaker direction: " + display_text(result.get("geometry_hint")))
        with st.expander("Engine reasoning"):
            for step in result["reasoning_steps"]:
                st.write(f"- {clean_text(step)}")


def get_equivalent_bucket(iso_group: str, zone: str) -> dict[str, Any] | None:
    rows = load_json("equivalents/grade_equivalents.json") or []
    for row in rows:
        if row.get("iso_group") == iso_group and row.get("zone") == zone:
            return row
    return None


def get_grade_rows(iso_group: str, zone: str, tool_category: str) -> list[dict[str, Any]]:
    rows = load_json("grade_maps/grades.json") or []
    matched = [
        row
        for row in rows
        if row.get("primary_iso_group") == iso_group
        and row.get("zone") == zone
        and tool_category in row.get("tool_categories", [])
    ]
    matched.sort(key=lambda r: (r.get("brand", ""), r.get("grade", "")))
    return matched


def render_metric_strip(metrics: list[tuple[str, str]]) -> None:
    cols = st.columns(len(metrics))
    for col, (label, value) in zip(cols, metrics):
        col.metric(label, value)


def render_catalog_explorer() -> None:
    st.subheader("Catalog Data Explorer")
    manifest = load_json("tool_data_manifest.json") or {"record_counts": {}}
    counts = manifest.get("record_counts", {})

    render_metric_strip(
        [
            ("Grades", str(counts.get("grades", 0))),
            ("Turning", str(counts.get("turning_inserts", 0))),
            ("Drills", str(counts.get("solid_drills", 0) + counts.get("indexable_drills", 0))),
            ("Milling", str(counts.get("endmills", 0) + counts.get("indexable_cutters", 0))),
        ]
    )
    st.caption("Use this screen to show the demo is backed by curated catalog-family records rather than hard-coded examples.")

    datasets = {
        "Grade Map": "grade_maps/grades.json",
        "Turning Insert Families": "normalized/turning/inserts.json",
        "Turning Holder Families": "normalized/turning/toolholders.json",
        "Grooving Insert Families": "normalized/grooving/inserts.json",
        "Threading Insert Families": "normalized/threading/inserts.json",
        "Solid Drill Families": "normalized/drilling/solid_drills.json",
        "Indexable Drill Families": "normalized/drilling/indexable_drills.json",
        "Endmill Families": "normalized/milling/endmills.json",
        "Indexable Milling Cutters": "normalized/milling/indexable_cutters.json",
        "Burnishing Tools": "normalized/burnishing/tools.json",
        "Workholding": "normalized/workholding/chucks.json",
    }

    choice = st.selectbox("Dataset", list(datasets.keys()))
    rows = load_json(datasets[choice]) or []
    st.write(f"{choice}: **{len(rows)}** records loaded")
    if rows:
        df = pd.json_normalize(rows)
        st.dataframe(df, **dataframe_display_kwargs(height=450))


def render_tool_lookup() -> None:
    st.subheader("Tool Lookup / Cross Reference")
    st.caption("Use manufacturer numbers, insert designations, or series names to find likely family matches and comparable alternatives.")
    records = load_lookup_records()
    categories = sorted({record.get("tool_category", "") for record in records if record.get("tool_category")})
    brands = sorted({record.get("brand", "") for record in records if record.get("brand")})

    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        query = st.text_input("Search", placeholder="CNMG 432, CoroMill 490, 16ER AG60")
    with c2:
        category_filter = st.selectbox("Tool Category", ["Any"] + categories)
    with c3:
        brand_filter = st.selectbox("Brand", ["Any"] + brands)

    if not query.strip():
        st.info("Enter a manufacturer number, designation, or series to run the cross-reference search.")
        return

    result = cross_reference_tool(
        query,
        tool_category=None if category_filter == "Any" else category_filter,
        brand=None if brand_filter == "Any" else brand_filter,
    )

    if result["exact_match"]:
        exact = result["exact_match"]
        st.markdown("#### Exact Match")
        with st.container(border=True):
            st.write(f"**{clean_text(exact.get('brand', ''))} — {clean_text(exact.get('series', ''))}**")
            st.write(f"Reference: {clean_text(exact.get('manufacturer_reference', exact.get('manufacturer_number', '')))}")
            st.write(f"Category: {clean_text(exact.get('tool_category', ''))}")
            if exact.get("designation"):
                st.write(f"Designation: {clean_text(exact['designation'])}")
            if exact.get("grade"):
                st.write(f"Grade: {clean_text(exact['grade'])}")
            st.write(f"Materials: {compact_list(exact.get('materials', {}).get('iso_groups', []))}")
            st.write(f"Application: {format_mapping(exact.get('application', {}))}")
            st.caption(f"Search hint: {clean_text(exact.get('search_hint', ''))}")

    st.markdown("#### Alternatives")
    if result["alternatives"]:
        for alternative in result["alternatives"]:
            with st.container(border=True):
                st.write(f"**{clean_text(alternative.get('brand', ''))} — {clean_text(alternative.get('series', ''))}**")
                st.write(f"Reference: {clean_text(alternative.get('manufacturer_reference', ''))}")
                st.write(f"Category: {clean_text(alternative.get('tool_category', ''))}")
                st.write(f"Match score: {alternative.get('score', 0)}")
                if alternative.get("match_reasons"):
                    st.write("Match reasons: " + " | ".join(clean_text(reason) for reason in alternative["match_reasons"]))
                st.caption(f"Search hint: {clean_text(alternative.get('search_hint', ''))}")
    else:
        st.info("No alternatives found in the current lookup index.")

    if result["warnings"]:
        for warning in result["warnings"]:
            st.warning(clean_text(warning))

    render_lookup_brand_intelligence(query)


def render_lookup_brand_intelligence(query: str) -> None:
    inferred = infer_brand_intelligence_from_query(query)
    has_matches = bool(
        inferred["matched_terms"]
        or inferred["brand_matches"]
        or inferred["operation_matches"]
        or inferred["recommended_brands"]
        or inferred["endmill_candidates"]
        or inferred["insert_candidates"]
    )
    if not has_matches:
        return

    with st.expander("Brand Intelligence Match", expanded=True):
        st.caption("Supplemental family-level guidance only. Normal Tool Lookup results above are unchanged.")
        st.write("Matched terms: " + compact_list(inferred["matched_terms"]))
        if inferred["operation_matches"]:
            st.write("Operation direction: " + compact_list(inferred["operation_matches"]))

        if inferred["recommended_brands"]:
            st.markdown("##### Recommended Brand Families")
            for item in inferred["recommended_brands"]:
                render_family_recommendation_card(
                    header=clean_text(item["brand"]),
                    direction="Use this brand as a family-level starting point for the matched lookup context.",
                    family_value=compact_list(item.get("best_fit_operations", [])),
                    family_label="Suggested family focus",
                    why_this_fits=format_reason_text(item.get("reasons", [])),
                    reviewed_support_record=item,
                    source_lines=[clean_text(note) for note in item.get("shop_use_notes", [])[:2]],
                    raw_scoring_lines=[f"Score: {item['score']}"],
                )

        if inferred["endmill_candidates"]:
            st.markdown("##### Endmill Candidates")
            for item in inferred["endmill_candidates"]:
                with st.container(border=True):
                    st.write(f"**{clean_text(item['brand'])}** — {clean_text(item['family_name'])}")
                    st.caption("Fit: " + compact_list(item.get("operation_fit", [])))
                    if item.get("cautions"):
                        st.caption(clean_text(item["cautions"][0]))

        if inferred["insert_candidates"]:
            st.markdown("##### Insert Candidates")
            for item in inferred["insert_candidates"]:
                with st.container(border=True):
                    st.write(f"**{clean_text(item['brand'])}** | Score: {item['score']}")
                    st.caption("Application fit: " + compact_list(item.get("application_fit", [])))
                    if item.get("shop_use_notes"):
                        st.caption(clean_text(item["shop_use_notes"][0]))

        for note in inferred["notes"]:
            st.caption(clean_text(note))
        st.caption(clean_text(inferred["verification_note"]))


def render_brand_intelligence() -> None:
    st.subheader("Brand Intelligence")
    st.info("Family-level guidance only. Verify exact tool selection, geometry, dimensions, and cutting data with the manufacturer catalog.")

    operations = [
        "general_milling",
        "dynamic_milling",
        "aluminum_milling",
        "drilling",
        "threading",
        "turning",
        "grooving",
        "small_bore",
        "specialty",
        "keyseat",
        "chamfer",
        "production_turning",
    ]
    priorities = [
        "balanced",
        "value",
        "high_performance",
        "specialty",
        "production_turning",
        "small_bore",
    ]
    brand_types = sorted({item for record in load_brand_intelligence() for item in record.get("brand_type", [])})

    c1, c2, c3, c4 = st.columns([1.2, 1.1, 1.1, 1.2])
    with c1:
        operation = st.selectbox("Operation", operations, format_func=titleize_token)
    with c2:
        material_group = st.selectbox(
            "Material Group",
            ["P", "M", "K", "N", "S", "H"],
            format_func=lambda value: MATERIAL_GROUP_LABELS[value],
        )
    with c3:
        priority = st.selectbox("Priority", priorities, format_func=titleize_token)
    with c4:
        brand_type_filter = st.selectbox("Brand Type", ["Any"] + brand_types, format_func=lambda value: "Any" if value == "Any" else titleize_token(value))

    minimum_score = st.slider("Minimum Score", min_value=1, max_value=12, value=1, step=1)

    recommendations = recommend_brand_families(operation, material_group, priority)
    if brand_type_filter != "Any":
        recommendations = [
            recommendation
            for recommendation in recommendations
            if brand_type_filter in recommendation.get("brand_type", [])
        ]
    recommendations = [
        recommendation
        for recommendation in recommendations
        if recommendation.get("score", 0) >= minimum_score
    ]
    if not recommendations:
        st.warning("No family-level brand candidates found for this combination.")
        return

    for recommendation in recommendations[:8]:
        with st.container(border=True):
            header, status = st.columns([2.4, 1])
            with header:
                st.markdown(f"#### {clean_text(recommendation['brand'])}")
            with status:
                st.metric("Score", recommendation["score"])
                st.caption(clean_text(recommendation["source_status"]))
            if recommendation.get("reasons"):
                st.write("Why it fits: " + " | ".join(clean_text(reason) for reason in recommendation["reasons"]))
            detail_cols = st.columns(3)
            with detail_cols[0]:
                st.write(f"Best-fit operations: {compact_list(recommendation.get('best_fit_operations', []))}")
            with detail_cols[1]:
                st.write(f"Material strengths: {compact_list(recommendation.get('material_strengths', []))}")
            with detail_cols[2]:
                st.write(f"Engine use: {compact_list(recommendation.get('recommended_engine_use', []))}")
            for note in recommendation.get("shop_use_notes", []):
                st.caption(clean_text(note))
            if recommendation.get("official_source_url"):
                st.caption(
                    f"Source: [{clean_text(recommendation.get('official_source_label', 'Official source'))}]"
                    f"({recommendation['official_source_url']}) | Verification: {clean_text(recommendation.get('verification_level', ''))}"
                )

    with st.expander("Problem Solver"):
        problem_types = [
            "chatter",
            "poor_finish",
            "short_tool_life",
            "chip_control",
            "small_bore_access",
            "needs_value_option",
            "dynamic_milling",
            "specialty_feature",
            "production_turning",
        ]
        pc1, pc2, pc3, pc4, pc5 = st.columns([1.2, 1.1, 1, 1, 1])
        with pc1:
            problem_type = st.selectbox("Problem", problem_types, format_func=titleize_token)
        with pc2:
            problem_operation = st.selectbox("Problem Operation", operations, format_func=titleize_token)
        with pc3:
            problem_material = st.selectbox(
                "Problem Material",
                ["P", "M", "K", "N", "S", "H"],
                format_func=lambda value: MATERIAL_GROUP_LABELS[value],
            )
        with pc4:
            problem_priority = st.selectbox("Problem Priority", priorities, format_func=titleize_token)
        with pc5:
            setup_rigidity = st.selectbox("Setup Rigidity", ["good", "average", "poor"], format_func=titleize_token)

        solution = solve_operation_problem(problem_type, problem_material, problem_operation, problem_priority, setup_rigidity)
        st.write(clean_text(solution["recommended_direction"]))
        if solution["brand_family_candidates"]:
            st.write("Brand candidates: " + compact_list([item["brand"] for item in solution["brand_family_candidates"]]))
        if solution["endmill_candidates"]:
            st.write("Endmill candidates: " + compact_list([item["brand"] for item in solution["endmill_candidates"]]))
        if solution["insert_candidates"]:
            st.write("Insert candidates: " + compact_list([item["brand"] for item in solution["insert_candidates"]]))
        for caution in solution["cautions"]:
            st.caption(clean_text(caution))
        st.caption(clean_text(solution["verification_note"]))

    render_reviewed_catalog_families()


def render_reviewed_catalog_families() -> None:
    with st.expander("Reviewed Catalog Families"):
        st.caption("Reviewed catalog families are reference-only and do not provide certified speeds/feeds.")
        summary = get_reviewed_catalog_summary()
        if summary["total_records"] == 0:
            st.info("No reviewed catalog family records yet. Stage and review catalog families before they appear here.")
            return

        render_metric_strip(
            [
                ("Records", str(summary["total_records"])),
                ("Brands", str(len(summary["brands"]))),
                ("Categories", str(len(summary["tool_categories"]))),
                ("Operations", str(len(summary["operations"]))),
            ]
        )

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            brand = st.selectbox("Reviewed Brand", ["Any"] + summary["brands"])
        with c2:
            tool_category = st.selectbox("Reviewed Category", ["Any"] + summary["tool_categories"], format_func=lambda value: "Any" if value == "Any" else titleize_token(value))
        with c3:
            material_group = st.selectbox("Reviewed Material", ["Any"] + summary["materials"])
        with c4:
            operation = st.selectbox("Reviewed Operation", ["Any"] + summary["operations"], format_func=lambda value: "Any" if value == "Any" else titleize_token(value))

        records = filter_reviewed_catalog_records(
            brand=None if brand == "Any" else brand,
            tool_category=None if tool_category == "Any" else tool_category,
            material_group=None if material_group == "Any" else material_group,
            operation=None if operation == "Any" else operation,
        )
        if not records:
            st.info("No reviewed catalog family records match these filters.")
            return

        for record in records[:12]:
            with st.container(border=True):
                st.write(f"**{clean_text(record.get('brand', ''))} — {clean_text(record.get('family_name', ''))}**")
                st.write(f"Category: {clean_text(record.get('tool_category', ''))}")
                st.write(f"Operations: {compact_list(record.get('operation_fit', []))}")
                st.write(f"Materials: {compact_list(record.get('material_fit', []))}")
                st.caption(clean_text(record.get("dimension_summary", "")))
                if record.get("source_url"):
                    st.caption(
                        f"Source: [{clean_text(record.get('source_label', 'Catalog source'))}]"
                        f"({record['source_url']})"
                    )
                st.caption(f"Status: {clean_text(record.get('verification_status', ''))} | Cutting data: {clean_text(record.get('cutting_data_status', ''))}")


def build_common_inputs() -> dict[str, Any]:
    st.subheader("Machining Conditions")
    st.caption("Tell the engine about the material, setup, machine situation, and what matters most. The answer cards below stay focused on the recommendation first.")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown("#### Material")
        material_group = st.selectbox(
            "Material Group",
            MATERIAL_GROUPS,
            index=0,
            format_func=lambda x: MATERIAL_GROUP_LABELS[x],
        )
        application_zone = st.selectbox("Application Zone", APPLICATION_ZONES, index=1)
    with c2:
        st.markdown("#### Setup")
        interrupted_cut = st.selectbox("Interrupted Cut", INTERRUPTED_CUT, index=0)
        stickout = st.selectbox("Stickout", STICKOUT, index=1)
    with c3:
        st.markdown("#### Machine / Rigidity")
        workholding = st.selectbox("Workholding", WORKHOLDING, index=0)
        cutting_speed_band = st.selectbox("Cutting Speed Band", CUTTING_SPEED_BAND, index=1)
    with c4:
        st.markdown("#### Goal / Priority")
        doc_band = st.selectbox("DOC Band", DOC_BAND, index=1)
        finish_priority = st.selectbox("Finish Priority", FINISH_PRIORITY, index=1)

    return {
        "material_group": material_group,
        "application_zone": application_zone,
        "interrupted_cut": interrupted_cut,
        "stickout": stickout,
        "workholding": workholding,
        "cutting_speed_band": cutting_speed_band,
        "doc_band": doc_band,
        "finish_priority": finish_priority,
    }


def recommend_turning(common: dict[str, Any]) -> None:
    p_steel_shop_note = (
        "Shop preference for P steel: PF for finish/light-to-medium steel turning, "
        "PR for rougher/heavier steel turning. MF/MR remain valid catalog alternatives "
        "depending on insert family and supplier."
    )
    intent_note = (
        "Turning intent is a shop-facing guide layered on top of DOC, finish priority, "
        "setup stability, and catalog fit."
    )
    operation = st.selectbox("Turning Operation", ["Longitudinal turning", "Facing", "Profiling", "Plunging"])
    turning_intent = st.selectbox("Turning Intent", TURNING_INTENTS, index=1)
    rows = load_json("normalized/turning/inserts.json") or []
    blob_terms = {
        "Longitudinal turning": ["longitudinal", "turning", "general"],
        "Facing": ["facing"],
        "Profiling": ["profiling"],
        "Plunging": ["plunging"],
    }
    structured_operations = {
        "Longitudinal turning": ["longitudinal_turning"],
        "Facing": ["facing"],
        "Profiling": ["profiling"],
        "Plunging": ["plunging"],
    }
    result = resolve_grade_behavior(common)
    intent_profile = build_turning_intent_profile(common, turning_intent)
    identity = result["insert_identity"]
    target_chipbreaker = result["chipbreaker_hint"]["family"].split("/")[0].strip().upper()
    scored = []
    for row in rows:
        if not has_iso_group(row, common["material_group"]):
            continue
        reasons: list[str] = []
        blob = text_blob(row)
        score = match_terms(blob, blob_terms[operation])
        operations = row.get("application", {}).get("operations", [])
        if any(term in operations for term in structured_operations[operation]):
            score += 4
            reasons.append("operation family matches")
        if row.get("engine_zone") == common["application_zone"]:
            score += 3
            reasons.append(f"{common['application_zone'].lower()} zone family")
        if row.get("designation_family", "").upper() == identity["shape"]:
            score += 4
            reasons.append(f"{identity['shape']} shape alignment")
        chipbreaker = str(row.get("geometry", {}).get("chipbreaker", "")).upper()
        if target_chipbreaker and target_chipbreaker in chipbreaker:
            score += 2
            reasons.append(f"{target_chipbreaker} chipbreaker direction")
        intent_weight = intent_profile["chipbreaker_weights"].get(chipbreaker, 0)
        if intent_weight:
            score += intent_weight
            reasons.append(f"{turning_intent.lower()} intent favors {chipbreaker}")
        intent_hits = match_terms(blob, intent_profile["keyword_terms"])
        if intent_hits:
            score += intent_hits
            reasons.append(f"{turning_intent.lower()} intent wording")
        if result["required_toughness"] == "HIGH":
            score += match_terms(blob, ["rough", "mr", "smr", "heavy"])
            if score:
                reasons.append("toughness-side geometry")
        elif result["required_wear_resistance"] == "HIGH":
            score += match_terms(blob, ["finish", "wiper", "wf", "pf", "xf"])
            if score:
                reasons.append("wear-side / finishing bias")
        else:
            score += match_terms(blob, ["medium", "mf", "balanced", "general"])
            if score:
                reasons.append("balanced family")
        if common["material_group"] == "P":
            score += match_terms(blob, ["steel", "p"])
            if common["application_zone"] == "TOUGH" or common["doc_band"] == "HEAVY":
                if chipbreaker == "PR":
                    score += 2
                    reasons.append("shop-preferred PR steel roughing direction")
                elif chipbreaker in {"MF", "MR"}:
                    score += 1
                    reasons.append("MF/MR remain valid catalog steel alternatives")
            else:
                if chipbreaker == "PF":
                    score += 2
                    reasons.append("shop-preferred PF steel finishing direction")
                elif chipbreaker in {"MF", "MR"}:
                    score += 1
                    reasons.append("MF/MR remain valid catalog steel alternatives")
        elif common["material_group"] == "M":
            score += match_terms(blob, ["stainless", "m"])
        elif common["material_group"] == "K":
            score += match_terms(blob, ["cast iron", "k"])
        scored.append((score, row, reasons))
    scored.sort(key=lambda x: (-x[0], x[1].get("brand", ""), x[1].get("designation_family", "")))

    st.subheader("Recommended Turning Direction")
    with st.container(border=True):
        st.markdown(f"### {clean_text(result['recommendation_title'])}")
        st.write(clean_text(result["recommendation_summary"]))
        st.write(f"**Recommended direction:** {clean_text(result.get('tool_direction', result['recommendation_title']))}")
        st.write(f"**Suggested tool/insert family:** {clean_text(identity['identity_summary'])}")
        st.write(f"**Why this fits:** {clean_text(result['recommendation_fit_sentence'])}")
        render_metric_strip(
            [
                ("Turning Intent", clean_text(turning_intent)),
                ("Insert Shape", clean_text(identity["shape"])),
                ("Chipbreaker", clean_text(result["chipbreaker_hint"]["family"])),
                ("Coating", clean_text(result["preferred_coating"])),
            ]
        )
        if result["risk_flags"]:
            st.warning("Risks / cautions: " + " | ".join(clean_text(flag) for flag in result["risk_flags"]))
        render_verification_note()
        with st.expander("Source/details"):
            st.write(
                f"Starting insert direction: {clean_text(identity['identity_summary'])}. "
                f"Chipbreaker bias: {clean_text(result['chipbreaker_hint']['family'])}."
            )
            st.write(
                f"Turning intent: {clean_text(turning_intent)} | "
                f"{clean_text(intent_profile['intent_caption'])} "
                f"Edge direction: {clean_text(intent_profile['edge_direction'])} "
                f"Nose-radius direction: {clean_text(intent_profile['nose_radius_direction'])}"
            )
            st.write(clean_text(intent_note))
            if common["material_group"] == "P":
                st.write(clean_text(p_steel_shop_note))

    eq = get_equivalent_bucket(common["material_group"], common["application_zone"])
    grades = get_grade_rows(common["material_group"], common["application_zone"], "turning_insert")
    col1, col2 = st.columns([2, 3])
    with col1:
        st.markdown("#### Grade bucket")
        if eq:
            for cand in eq.get("candidates", [])[:6]:
                st.write(f"- **{clean_text(cand['brand'])}** — {clean_text(cand['grade'])}")
        else:
            st.write("No equivalence bucket found.")
    with col2:
        st.markdown("#### Matching grade records")
        if grades:
            st.dataframe(
                preferred_frame(grades, ["brand", "grade", "zone", "coating", "tags"]),
                **dataframe_display_kwargs(height=220),
            )
        else:
            st.write("No grade rows found.")

    st.markdown("#### Suggested Turning Families")
    for score, row, reasons in scored[:5]:
        render_family_recommendation_card(
            header=f"{clean_text(row.get('brand', ''))} - {clean_text(row.get('series', ''))}",
            direction=f"{operation} family with {clean_text(row.get('geometry', {}).get('chipbreaker', 'general'))} chipbreaker direction.",
            family_value=clean_text(row.get('designation_family', row.get('id', ''))),
            why_this_fits=format_reason_text(reasons),
            source_lines=[
                f"Materials: {compact_list(row.get('materials', {}).get('iso_groups', []))}",
                f"Chipbreaker: {clean_text(row.get('geometry', {}).get('chipbreaker', 'Not listed'))}",
                f"Recommended grades: {compact_list(row.get('recommended_grades', []))}",
                clean_text(row.get('notes', '')),
            ],
            raw_scoring_lines=[f"Fit score: {score}"],
        )
    _turning_op_map = {
        "Longitudinal turning": "external_turning",
        "Facing": "facing",
        "Profiling": "profiling",
        "Plunging": "plunging",
    }
    _render_exact_tool_candidates_expander(
        suggest_tool_candidates(
            _turning_op_map.get(operation, "external_turning"),
            common["material_group"],
            tool_category="turning_insert",
        ),
        operation,
        common["material_group"],
    )


def recommend_drilling(common: dict[str, Any]) -> None:
    selected_drill_type = st.selectbox("Drill Type", ["Solid Carbide Drill", "Indexable Drill"])
    diameter = st.number_input("Hole Diameter (mm)", min_value=0.5, max_value=80.0, value=12.0, step=0.5)
    ld = st.selectbox("Depth Ratio (L/D)", [1, 2, 3, 4, 5, 8, 10, 12, 15, 20, 25, 30], index=4)
    engine_result = resolve_drilling_engine(
        {
            **common,
            "drill_type": selected_drill_type,
            "diameter_mm": diameter,
            "l_d_ratio": ld,
        }
    )
    drill_type = engine_result["drill_type"]
    path = "normalized/drilling/solid_drills.json" if drill_type == "Solid Carbide Drill" else "normalized/drilling/indexable_drills.json"
    rows = load_json(path) or []
    scored = []
    for row in rows:
        if not has_iso_group(row, common["material_group"]):
            continue
        score = 0
        reasons: list[str] = []
        geom = row.get("geometry", {})
        if drill_type == "Solid Carbide Drill":
            rng = geom.get("diameter_range_mm", [0, 999])
            available_ld = geom.get("available_l_d", [])
            if rng and rng[0] <= diameter <= rng[1]:
                score += 4
                reasons.append("diameter in range")
            elif diameter < rng[0] or diameter > rng[1]:
                score -= 2
            if ld in available_ld:
                score += 4
                reasons.append("exact L/D match")
            elif available_ld:
                score += max(0, 3 - min(abs(ld - x) for x in available_ld))
            if geom.get("coolant") == "internal":
                score += 1
                if "strongly preferred" in engine_result["coolant_preference"].lower():
                    score += 1
                reasons.append("coolant direction matches")
            if engine_result["geometry_bias"].startswith("Sharper"):
                score += match_terms(text_blob(row), ["micro", "solid", "precision"])
                if score:
                    reasons.append("sharper solid-drill direction")
            if engine_result["stability_bias"] != "HIGH":
                score += 1
                reasons.append("solid-drill stability bias")
            if common["cutting_speed_band"] == "HIGH":
                score += 1
                reasons.append("speed-friendly carbide bias")
        else:
            l_d = geom.get("l_d")
            rng = geom.get("diameter_range_mm", [0, 999])
            if rng and rng[0] <= diameter <= rng[1]:
                score += 4
                reasons.append("diameter in range")
            if l_d == ld:
                score += 4
                reasons.append("exact L/D match")
            elif isinstance(l_d, int):
                score += max(0, 3 - abs(ld - l_d))
            if engine_result["stability_bias"] == "HIGH":
                score += 1
                reasons.append("setup allows indexable productivity")
            if diameter >= 20:
                score += 1
                reasons.append("larger-diameter fit")
            if engine_result["geometry_bias"].startswith("Stronger"):
                score += 1
                reasons.append("stronger point-direction fit")
        if common["material_group"] in row.get("materials", {}).get("iso_groups", []):
            score += 2
            reasons.append(f"{common['material_group']} material coverage")
        if engine_result["stability_bias"] == "LOW":
            score -= 1
            reasons.append("flagged for setup stability review")
        scored.append((score, row, reasons))
    scored.sort(key=lambda x: (-x[0], x[1].get("brand", ""), x[1].get("series", "")))

    st.subheader("Recommended Drilling Direction")
    render_tool_engine_result(
        engine_result,
        [
            ("Drill Type", engine_result["drill_type"]),
            ("Coolant", "Strong" if "strongly" in engine_result["coolant_preference"].lower() else "Preferred"),
            ("Stability", engine_result["stability_bias"]),
            ("Point Bias", engine_result["geometry_bias"].split()[0]),
        ],
    )
    st.write(f"Target: **{diameter:.1f} mm**, **{ld}xD**, **{MATERIAL_GROUP_LABELS[common['material_group']]}**")
    st.caption(DRILL_TYPE_HINTS[engine_result["drill_type"]])
    if selected_drill_type != engine_result["drill_type"]:
        st.info(f"Selected type: {selected_drill_type}. Engine direction: {engine_result['drill_type']}.")
    if not scored:
        alternate = "Solid Carbide Drill" if drill_type == "Indexable Drill" else "Catalog Data Explorer"
        render_empty_state("drilling", common["material_group"], f"Try {alternate} for this material group in the current demo dataset.")
        return

    for score, row, reasons in scored[:6]:
        geom = row.get("geometry", {})
        grade = row.get("grade_or_coating") or row.get("insert_system", {}).get("grade")
        render_family_recommendation_card(
            header=f"{clean_text(row.get('brand', ''))} - {clean_text(row.get('series', ''))}",
            direction=f"{clean_text(engine_result['drill_type'])} family aligned to {ld}xD holemaking.",
            family_value=clean_text(row.get('subcategory', row.get('tool_category', 'drill'))),
            why_this_fits=format_reason_text(reasons),
            source_lines=[
                f"Diameter range: {geom['diameter_range_mm'][0]} to {geom['diameter_range_mm'][1]} mm" if geom.get("diameter_range_mm") else "",
                f"Available L/D: {geom['available_l_d']}" if geom.get("available_l_d") else "",
                f"L/D: {geom['l_d']}" if geom.get("l_d") and not geom.get("available_l_d") else "",
                f"Coolant: {clean_text(geom.get('coolant', ''))}" if geom.get("coolant") else "",
                f"Grade / coating: {clean_text(grade)}" if grade else "",
            ],
            raw_scoring_lines=[f"Fit score: {score}"],
        )
    _drill_cat = "drill" if drill_type == "Solid Carbide Drill" else "indexable_drill"
    _render_exact_tool_candidates_expander(
        suggest_tool_candidates(
            "drilling",
            common["material_group"],
            tool_category=_drill_cat,
        ),
        "drilling",
        common["material_group"],
    )


def recommend_milling(common: dict[str, Any], mode: str) -> None:
    if mode == "ENDMILL":
        rows = load_json("normalized/milling/endmills.json") or []
        operation_options = {
            "Profiling": ["profiling", "general"],
            "Slotting": ["slotting"],
            "High Velocity": ["high_velocity", "high velocity"],
            "Roughing": ["roughing", "rough_finish", "trochoidal_milling"],
            "Finishing": ["finish", "semi_finish"],
        }
        operation_label = st.selectbox("Endmill Strategy", list(operation_options.keys()))
        engine_result = resolve_endmill_engine({**common, "operation": operation_label})
    else:
        rows = load_json("normalized/milling/indexable_cutters.json") or []
        operation_options = {
            "Facing": ["face_milling", "facing"],
            "Shoulder Milling": ["shoulder_milling"],
            "Plunge Milling": ["plunge_milling", "plunging", "high_feed_milling"],
            "Slotting": ["slotting"],
        }
        operation_label = st.selectbox("Face Mill Operation", list(operation_options.keys()))
        engine_result = resolve_facemill_engine({**common, "operation": operation_label})
    operation_terms = operation_options[operation_label]
    scored = []
    for row in rows:
        if not has_iso_group(row, common["material_group"]):
            continue
        reasons: list[str] = []
        blob = text_blob(row)
        score = match_terms(blob, operation_terms)
        application = row.get("application", {})
        operations = application.get("operations", [])
        strategy = application.get("strategy", "")
        geom = row.get("geometry", {})
        if mode == "ENDMILL":
            if strategy == engine_result["strategy_bias"] or strategy in operation_terms:
                score += 5
                reasons.append(f"{operation_label.lower()} strategy match")
            if match_terms(blob, [application.get("materials_focus", "")]):
                score += 1
            flute_count = geom.get("flute_count") or 0
            if not isinstance(flute_count, Real):
                flute_count = 0
            if "2-3" in engine_result["flute_count_direction"] and flute_count <= 3:
                score += 2
                reasons.append("lower flute-count direction")
            elif "4-6" in engine_result["flute_count_direction"] and flute_count >= 4:
                score += 2
                reasons.append("finish-side flute direction")
            elif "4 flute" in engine_result["flute_count_direction"] and flute_count == 4:
                score += 2
                reasons.append("general-purpose flute direction")
        else:
            if any(term in operations for term in operation_terms):
                score += 5
                reasons.append(f"{operation_label.lower()} cutter coverage")
            if engine_result["cutter_style"] == "high_feed":
                score += match_terms(blob, ["high_feed", "plunge", "feedmill"])
                if match_terms(blob, ["high_feed", "plunge", "feedmill"]):
                    reasons.append("high-feed engine direction")
            elif engine_result["cutter_style"] == "shoulder":
                score += match_terms(blob, ["shoulder", "90_degree"])
                if match_terms(blob, ["shoulder", "90_degree"]):
                    reasons.append("shoulder engine direction")
            else:
                score += match_terms(blob, ["face", "45_degree", "88_degree"])
                if match_terms(blob, ["face", "45_degree", "88_degree"]):
                    reasons.append("face-mill engine direction")
            edges = geom.get("cutting_edges_per_insert") or 0
            if not isinstance(edges, Real):
                edges = 0
            if "higher" in engine_result["insert_density"] and edges >= 8:
                score += 2
                reasons.append("higher insert-density direction")
            elif "moderate" in engine_result["insert_density"] and 4 <= edges <= 8:
                score += 2
                reasons.append("moderate insert-density direction")
            elif "lower" in engine_result["insert_density"] and 0 < edges <= 6:
                score += 2
                reasons.append("lower insert-density direction")
        if common["application_zone"] == "TOUGH":
            score += match_terms(blob, ["rough", "heavy", "plunge", "shoulder", "high_feed"])
        elif common["application_zone"] == "WEAR":
            score += match_terms(blob, ["finish", "high velocity", "semi finish", "fine", "surface finish"])
        else:
            score += match_terms(blob, ["general", "facing", "profiling"])
        if common["finish_priority"] == "HIGH":
            score += match_terms(blob, ["finish", "semi_finish", "surface finish"])
        if common["doc_band"] == "HEAVY":
            score += match_terms(blob, ["rough", "high_feed", "shoulder", "plunge"])
        if common["material_group"] in row.get("materials", {}).get("iso_groups", []):
            reasons.append(f"{common['material_group']} material coverage")
        scored.append((score, row, reasons))
    scored.sort(key=lambda x: (-x[0], x[1].get("brand", ""), x[1].get("series", "")))

    title = "Recommended Endmill Direction" if mode == "ENDMILL" else "Recommended Face Mill Direction"
    st.subheader(title)
    if mode == "ENDMILL":
        render_tool_engine_result(
            engine_result,
            [
                ("Strategy", engine_result["strategy_bias"].replace("_", " ").title()),
                ("Flute Dir.", engine_result["flute_count_direction"].split()[0]),
                ("Chatter", engine_result["chatter_risk"]),
                ("Zone", common["application_zone"]),
            ],
        )
    else:
        render_tool_engine_result(
            engine_result,
            [
                ("Cutter Style", engine_result["cutter_style"].replace("_", " ").title()),
                ("Insert Density", engine_result["insert_density"].split()[0].title()),
                ("Zone", common["application_zone"]),
                ("DOC", common["doc_band"]),
            ],
        )
    if not scored:
        render_empty_state(title, common["material_group"], "Use Catalog Data Explorer to show the supported milling families in this demo dataset.")
        return

    for score, row, reasons in scored[:6]:
        geom = row.get('geometry', {})
        app = row.get('application', {})
        family_direction = operation_label if mode == 'ENDMILL' else engine_result['cutter_style'].replace('_', ' ')
        render_family_recommendation_card(
            header=f"{clean_text(row.get('brand', ''))} - {clean_text(row.get('series', ''))}",
            direction=f"{family_direction} milling family aligned to the selected planning direction.",
            family_value=clean_text(row.get('subcategory', row.get('tool_category', 'milling'))),
            why_this_fits=format_reason_text(reasons),
            source_lines=[
                f"Flutes: {geom['flute_count']}" if geom.get('flute_count') else "",
                f"Edges / insert: {geom['cutting_edges_per_insert']}" if geom.get('cutting_edges_per_insert') else "",
                f"Application: {format_mapping(app)}" if app else "",
            ],
            raw_scoring_lines=[f"Fit score: {score}"],
        )
    if mode == "ENDMILL":
        _mill_op_map = {
            "Profiling": "profiling",
            "Slotting": "slot_milling",
            "High Velocity": "general_milling",
            "Roughing": "roughing",
            "Finishing": "finishing",
        }
        _mill_op = _mill_op_map.get(operation_label, "general_milling")
        _mill_cat = "endmill"
    else:
        _mill_op_map = {
            "Facing": "face_milling",
            "Shoulder Milling": "shoulder_milling",
            "Plunge Milling": "plunge_milling",
            "Slotting": "slot_milling",
        }
        _mill_op = _mill_op_map.get(operation_label, "face_milling")
        _mill_cat = "milling_insert"
    _render_exact_tool_candidates_expander(
        suggest_tool_candidates(
            _mill_op,
            common["material_group"],
            tool_category=_mill_cat,
        ),
        operation_label,
        common["material_group"],
    )


def recommend_grooving(common: dict[str, Any]) -> None:
    operation_options = {
        "Grooving": ["grooving"],
        "Parting": ["parting", "cutoff"],
        "Face Grooving": ["face_grooving", "face grooving"],
        "Undercutting": ["undercutting"],
    }
    operation_label = st.selectbox("Grooving Operation", list(operation_options.keys()))
    engine_result = resolve_grooving_engine({**common, "operation": operation_label})
    operation_terms = operation_options[operation_label]
    rows = load_json("normalized/grooving/inserts.json") or []
    scored = []
    for row in rows:
        row_groups = row.get("materials", {}).get("iso_groups", [])
        if row_groups and common["material_group"] not in row_groups:
            continue
        blob = text_blob(row)
        reasons: list[str] = []
        score = match_terms(blob, operation_terms)
        operations = row.get("application", {}).get("operations", [])
        if any(term in operations for term in operation_terms):
            score += 5
            reasons.append(f"{operation_label.lower()} coverage")
        if engine_result["operation_type"] == "parting":
            score += match_terms(blob, ["cutoff", "parting", "wmt", "self-grip"])
            if match_terms(blob, ["cutoff", "parting", "wmt", "self-grip"]):
                reasons.append("parting-direction fit")
        elif engine_result["operation_type"] == "face_grooving":
            score += match_terms(blob, ["face_grooving", "topgroove", "ranger"])
            if match_terms(blob, ["face_grooving", "topgroove", "ranger"]):
                reasons.append("face-grooving direction")
        elif engine_result["operation_type"] == "undercutting":
            score += match_terms(blob, ["undercutting", "topgroove"])
            if match_terms(blob, ["undercutting", "topgroove"]):
                reasons.append("undercutting direction")
        else:
            score += match_terms(blob, ["grooving", "top-lok", "wmt"])
            if match_terms(blob, ["grooving", "top-lok", "wmt"]):
                reasons.append("general grooving direction")
        if common["application_zone"] == "TOUGH":
            score += match_terms(blob, ["heavy", "wmt", "progroove"])
        elif common["application_zone"] == "WEAR":
            score += match_terms(blob, ["topgroove", "precision", "finish"])
        if row_groups:
            reasons.append(f"{common['material_group']} material coverage")
        scored.append((score, row, reasons))
    scored.sort(key=lambda x: (-x[0], x[1].get('brand', ''), x[1].get('series', '')))
    grades = get_grade_rows(common["material_group"], common["application_zone"], "grooving_insert")
    st.subheader("Recommended Grooving Direction")
    render_tool_engine_result(
        engine_result,
        [
            ("Operation", operation_label),
            ("Blade Dir.", engine_result["blade_rigidity"].split()[0].title()),
            ("Chip Evac.", engine_result["chip_evacuating_priority"]),
            ("Zone", common["application_zone"]),
        ],
    )
    st.caption("Insert-family records in this demo are mostly material-neutral here, so ISO-group sensitivity comes primarily from the matched grade bucket below.")
    if not scored:
        render_empty_state("grooving", common["material_group"])
        return

    for score, row, reasons in scored[:6]:
        geom = row.get('geometry', {})
        render_family_recommendation_card(
            header=f"{clean_text(row.get('brand', ''))} - {clean_text(row.get('series', ''))}",
            direction=f"{operation_label} family aligned to the selected grooving direction.",
            family_value=clean_text(row.get('designation_family', row.get('id', ''))),
            why_this_fits=format_reason_text(reasons),
            source_lines=[
                f"Geometry: {format_mapping(geom)}" if geom else "",
            ],
            raw_scoring_lines=[f"Fit score: {score}"],
        )
    _grooving_op_map = {
        "Grooving": "grooving",
        "Parting": "parting",
        "Face Grooving": "face_grooving",
        "Undercutting": "grooving",
    }
    _render_exact_tool_candidates_expander(
        suggest_tool_candidates(
            _grooving_op_map.get(operation_label, "grooving"),
            common["material_group"],
            tool_category="grooving_insert",
        ),
        operation_label,
        common["material_group"],
    )
    with st.expander("Matching grooving grades"):
        if grades:
            st.dataframe(
                preferred_frame(grades, ["brand", "grade", "zone", "coating", "tags"]),
                **dataframe_display_kwargs(),
            )
        else:
            st.write("No grooving grade rows found.")


def recommend_threading(common: dict[str, Any]) -> None:
    thread_options = {
        "External Threading": "external_threading",
        "Internal Threading": "internal_threading",
    }
    thread_label = st.selectbox("Threading Type", list(thread_options.keys()))
    pitch_hint = st.selectbox("Pitch Bias", ["Fine", "Medium", "Coarse"], index=1)
    thread_type = thread_options[thread_label]
    engine_result = resolve_threading_engine({**common, "thread_type": thread_type, "pitch_hint": pitch_hint})
    rows = load_json("normalized/threading/inserts.json") or []
    grades = get_grade_rows(common["material_group"], common["application_zone"], "threading_insert")
    grade_names = {row.get("grade") for row in grades}
    scored = []
    for row in rows:
        if not has_iso_group(row, common["material_group"]):
            continue
        reasons: list[str] = []
        blob = text_blob(row)
        score = match_terms(blob, [thread_type.replace("_", " "), thread_type])
        operations = row.get("application", {}).get("operations", [])
        if thread_type in operations:
            score += 5
            reasons.append(f"{thread_label.lower()} support")
        else:
            continue
        if engine_result["thread_profile_direction"] == "laydown":
            score += match_terms(blob, ["laydown", "266", "s-loc"])
            if match_terms(blob, ["laydown", "266", "s-loc"]):
                reasons.append("laydown-direction fit")
        else:
            score += match_terms(blob, ["16er", "16ir", "partial"])
            if match_terms(blob, ["16er", "16ir", "partial"]):
                reasons.append("partial-profile direction")
        matched_grades = [grade for grade in row.get("recommended_grades", []) if grade in grade_names]
        if matched_grades:
            score += 3
            reasons.append(f"grade bucket match: {', '.join(matched_grades[:2])}")
        if common["material_group"] == "P":
            score += match_terms(blob, ["pr930", "tc60", "steel"])
        if common["application_zone"] == "TOUGH":
            score += match_terms(blob, ["laydown", "266"])
        elif common["application_zone"] == "WEAR":
            score += match_terms(blob, ["precision", "266"])
        scored.append((score, row, reasons))
    scored.sort(key=lambda x: (-x[0], x[1].get('brand', ''), x[1].get('designation_family', '')))
    st.subheader("Recommended Threading Direction")
    render_tool_engine_result(
        engine_result,
        [
            ("Thread Type", "Internal" if engine_result["thread_access"] == "internal" else "External"),
            ("Profile Dir.", engine_result["thread_profile_direction"].title()),
            ("Pitch", engine_result["pitch_hint"]),
            ("Zone", common["application_zone"]),
        ],
    )
    if not scored:
        render_empty_state("threading", common["material_group"], "The current threading demo dataset is strongest for P, M, and K materials.")
        return

    for score, row, reasons in scored[:6]:
        render_family_recommendation_card(
            header=f"{clean_text(row.get('brand', ''))} - {clean_text(row.get('series', ''))}",
            direction=f"{thread_label} family aligned to the selected thread direction.",
            family_value=clean_text(row.get('designation_family', row.get('id', ''))),
            why_this_fits=format_reason_text(reasons),
            source_lines=[
                f"Operations: {compact_list(row.get('application', {}).get('operations', []))}",
                f"Recommended grades in dataset: {compact_list(row.get('recommended_grades', []))}",
            ],
            raw_scoring_lines=[f"Fit score: {score}"],
        )
    _render_exact_tool_candidates_expander(
        suggest_tool_candidates(
            thread_type,
            common["material_group"],
            tool_category="threading_insert",
        ),
        thread_label,
        common["material_group"],
    )
    with st.expander("Matching threading grades"):
        if grades:
            st.dataframe(
                preferred_frame(grades, ["brand", "grade", "zone", "coating", "tags"]),
                **dataframe_display_kwargs(),
            )
        else:
            st.write("No threading grade rows found.")


def recommend_burnishing() -> None:
    rows = load_json("normalized/burnishing/tools.json") or []
    st.subheader("Burnishing Recommendation")
    st.info("Use this when finish, size control, and surface work-hardening matter more than metal removal.")
    for row in rows[:6]:
        with st.container(border=True):
            st.write(f"**{clean_text(row.get('brand', ''))} — {clean_text(row.get('series', ''))}**")
            st.write(clean_text(row.get('subcategory', row.get('tool_category', 'burnishing_tool'))))
            st.write(f"Application: {format_mapping(row.get('application', {}))}")


def recommend_workholding() -> None:
    rows = load_json("normalized/workholding/chucks.json") or []
    st.subheader("Workholding Reference")
    st.info("Use this module to explain setup stability and quick-change capability during the demo.")
    for row in rows[:6]:
        with st.container(border=True):
            st.write(f"**{clean_text(row.get('brand', ''))} — {clean_text(row.get('series', ''))}**")
            st.write(f"Designation: {clean_text(row.get('designation', row.get('id', '')))}")
            st.write(f"Performance profile: {format_mapping(row.get('performance_profile', {}))}")


def _render_exact_tool_candidates_expander(
    candidates: list[dict[str, Any]],
    operation: str,
    material_group: str,
) -> None:
    with st.expander("Exact Tool Candidates"):
        if not candidates:
            st.caption(
                "No exact-tool candidates matched yet. "
                "Use Tooling Search for manual lookup."
            )
            return
        st.caption(
            f"Supplemental exact-tool candidates from the Enterprise Tooling Search index — "
            f"matched to **{operation}** / **{material_group}**. "
            "Verification status and cutting data status are shown on each card. "
            "These do not replace the recommendation families above."
        )
        norm_op = normalize_tool_query(operation).replace(" ", "_")
        mat = str(material_group).strip().upper()
        for record in candidates:
            reasons: list[str] = []
            if norm_op in record.get("operation_fit", []):
                reasons.append(f"operation matched: {norm_op}")
            if mat in record.get("material_fit", []):
                reasons.append(f"material matched: {mat}")
            if not reasons:
                reasons.append("matched from Enterprise Tooling Search index")
            _render_tooling_search_card(record, reasons)


def _render_tooling_search_card(record: dict[str, Any], reasons: list[str]) -> None:
    with st.container(border=True):
        h1, h2 = st.columns([3, 1])
        with h1:
            st.markdown(f"#### {clean_text(record['brand'])} — {clean_text(record['manufacturer_part_number'])}")
        with h2:
            st.caption(titleize_token(record.get("tool_category", "")))

        id_parts: list[str] = []
        if record.get("series"):
            id_parts.append(f"Series: {clean_text(record['series'])}")
        if record.get("family_name"):
            id_parts.append(f"Family: {clean_text(record['family_name'])}")
        if record.get("designation"):
            id_parts.append(f"Designation: {clean_text(record['designation'])}")
        if id_parts:
            st.write(" | ".join(id_parts))

        grade_parts: list[str] = []
        if record.get("grade"):
            grade_parts.append(f"Grade: {clean_text(record['grade'])}")
        if record.get("chipbreaker"):
            grade_parts.append(f"Chipbreaker: {clean_text(record['chipbreaker'])}")
        if record.get("coating"):
            grade_parts.append(f"Coating: {clean_text(record['coating'])}")
        if grade_parts:
            st.write(" | ".join(grade_parts))

        fit_c1, fit_c2 = st.columns(2)
        with fit_c1:
            if record.get("material_fit"):
                st.write(f"Materials: {compact_list(record['material_fit'])}")
        with fit_c2:
            if record.get("operation_fit"):
                st.write(f"Operations: {compact_list(record['operation_fit'][:5])}")

        if reasons:
            st.caption("Match: " + " | ".join(clean_text(r) for r in reasons[:4]))

        vstatus = record.get("verification_status", "")
        cds = record.get("cutting_data_status", "")
        status_parts: list[str] = []
        if vstatus:
            status_parts.append(titleize_token(vstatus))
        if cds:
            status_parts.append(f"Cutting data: {titleize_token(cds)}")
        if status_parts:
            st.caption(" | ".join(status_parts))

        if record.get("source_url"):
            ref = f" (p. {clean_text(record['source_page_reference'])})" if record.get("source_page_reference") else ""
            label = clean_text(record.get("source_label") or "Catalog source")
            st.caption(f"Source: [{label}]({record['source_url']}){ref}")

        detail_lines: list[str] = []
        if record.get("geometry_tags"):
            detail_lines.append(f"Geometry tags: {compact_list(record['geometry_tags'])}")
        if record.get("holder_compatibility"):
            detail_lines.append(f"Holder: {compact_list(record['holder_compatibility'])}")
        if record.get("coolant_capability") and record["coolant_capability"] != "unknown":
            detail_lines.append(f"Coolant: {titleize_token(record['coolant_capability'])}")
        if record.get("notes"):
            detail_lines.append(f"Notes: {clean_text(record['notes'])}")

        if detail_lines:
            with st.expander("Details"):
                for line in detail_lines:
                    st.write(line)

        with st.expander("Raw record"):
            st.json({k: v for k, v in record.items() if not k.startswith("_")})


def render_tooling_search() -> None:
    st.subheader("Enterprise Tooling Search")
    st.caption(
        "Search normalized tooling records by part number, family, designation, grade, or keyword. "
        "Filters narrow by category, material, operation, and more."
    )
    st.info(
        "Records are family-level reference only — no feeds, speeds, or certified cutting data. "
        "Verify all selections with the manufacturer catalog."
    )

    all_records = load_tooling_records()
    if not all_records:
        st.warning("No tooling search records loaded. Add records to tool_data/tooling_search/records/ to begin.")
        return

    brands = sorted({r["brand"] for r in all_records if r["brand"]})
    categories = sorted({r["tool_category"] for r in all_records if r["tool_category"]})
    operations = sorted({op for r in all_records for op in r.get("operation_fit", []) if op})
    geometry_tags = sorted({tag for r in all_records for tag in r.get("geometry_tags", []) if tag})

    query = st.text_input("Search", placeholder="CNMG 120408, CoroTurn, GC4325, TiAlN, turning insert…")

    fc1, fc2, fc3, fc4 = st.columns(4)
    with fc1:
        brand_f = st.selectbox("Brand", ["Any"] + brands)
    with fc2:
        category_f = st.selectbox(
            "Tool Category",
            ["Any"] + categories,
            format_func=lambda v: "Any" if v == "Any" else titleize_token(v),
        )
    with fc3:
        material_f = st.selectbox(
            "Material Group",
            ["Any", "P", "M", "K", "N", "S", "H"],
            format_func=lambda v: "Any" if v == "Any" else MATERIAL_GROUP_LABELS.get(v, v),
        )
    with fc4:
        operation_f = st.selectbox(
            "Operation",
            ["Any"] + operations,
            format_func=lambda v: "Any" if v == "Any" else titleize_token(v),
        )

    fc5, fc6, fc7, fc8 = st.columns(4)
    with fc5:
        grade_f = st.text_input("Grade contains", placeholder="GC4325, TT8020…")
    with fc6:
        chipbreaker_f = st.text_input("Chipbreaker contains", placeholder="MF, PM…")
    with fc7:
        coating_f = st.text_input("Coating contains", placeholder="TiAlN, CVD…")
    with fc8:
        geometry_tag_f = st.selectbox(
            "Geometry Tag",
            ["Any"] + geometry_tags,
            format_func=lambda v: "Any" if v == "Any" else titleize_token(v),
        )

    filters: dict[str, Any] = {}
    if brand_f != "Any":
        filters["brand"] = brand_f
    if category_f != "Any":
        filters["tool_category"] = category_f
    if material_f != "Any":
        filters["material_group"] = material_f
    if operation_f != "Any":
        filters["operation"] = operation_f
    if grade_f.strip():
        filters["grade"] = grade_f.strip()
    if chipbreaker_f.strip():
        filters["chipbreaker"] = chipbreaker_f.strip()
    if coating_f.strip():
        filters["coating"] = coating_f.strip()
    if geometry_tag_f != "Any":
        filters["geometry_tag"] = geometry_tag_f

    if not query.strip() and not filters:
        st.info(
            f"{len(all_records)} record(s) available across {len(brands)} brand(s). "
            "Enter a search term or apply a filter to find tools."
        )
        return

    results = search_tooling_records(query, filters or None)

    if not results:
        st.warning("No tooling records match this search and filter combination.")
        return

    shown = results[:20]
    suffix = f" — showing first {len(shown)}" if len(results) > len(shown) else ""
    st.write(f"**{len(results)}** record(s) found{suffix}.")

    for record in shown:
        reasons = explain_tool_match(record, query, filters or None)
        _render_tooling_search_card(record, reasons)


st.set_page_config(page_title="CNC Tooling Decision Engine", layout="wide")
st.title("CNC Tooling Decision Engine")
st.caption("Catalog-backed family selection and grade-behavior guidance for turning, drilling, milling, grooving, and threading demos.")
st.info("Demo note: this app is built to recommend credible tool families and grade direction. It is not a full SKU-complete selector.")

mode = st.radio("Mode", ["Decision Engine", "Tooling Search", "Catalog Data Explorer"], horizontal=True)
if mode == "Catalog Data Explorer":
    render_catalog_explorer()
    st.stop()
if mode == "Tooling Search":
    render_tooling_search()
    st.stop()

family = st.selectbox("Module", list(FAMILY_LABELS.keys()), format_func=lambda x: FAMILY_LABELS[x])
st.caption(MODULE_DESCRIPTIONS[family])

if family in {"BURNISHING", "WORKHOLDING", "TOOL_LOOKUP", "BRAND_INTELLIGENCE"}:
    if family == "BURNISHING":
        recommend_burnishing()
    elif family == "TOOL_LOOKUP":
        render_tool_lookup()
    elif family == "BRAND_INTELLIGENCE":
        render_brand_intelligence()
    else:
        recommend_workholding()
    st.stop()

common = build_common_inputs()
with st.expander("Engine Basis", expanded=False):
    behavior = resolve_grade_behavior(common)
    render_engine_basis(common, behavior)

if family == "TURNING_INSERT":
    recommend_turning(common)
elif family == "DRILL":
    recommend_drilling(common)
elif family == "ENDMILL":
    recommend_milling(common, "ENDMILL")
elif family == "FACE_MILL":
    recommend_milling(common, "FACE_MILL")
elif family == "GROOVING_INSERT":
    recommend_grooving(common)
elif family == "THREADING_INSERT":
    recommend_threading(common)
else:
    st.warning("This module is not wired yet.")
