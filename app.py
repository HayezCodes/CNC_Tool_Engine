import json
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
import streamlit as st

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
}

DRILL_TYPE_HINTS = {
    "Solid Carbide Drill": "Best when size control, reach, and smaller-diameter hole quality matter most.",
    "Indexable Drill": "Best when diameter is larger and the holemaking priority leans toward productivity and insert economy.",
}


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


def compact_list(values: Iterable[Any]) -> str:
    items = [str(value) for value in values if value not in (None, "", [], {})]
    return ", ".join(items) if items else "Not listed"


def format_mapping(mapping: dict[str, Any]) -> str:
    if not mapping:
        return "Not listed"
    return "; ".join(f"{titleize_token(str(key))}: {value}" for key, value in mapping.items())


def preferred_frame(rows: list[dict[str, Any]], preferred_columns: list[str]) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    columns = [column for column in preferred_columns if column in frame.columns]
    return frame[columns] if columns else frame


def render_empty_state(module_label: str, material_group: str, note: str | None = None) -> None:
    material_label = MATERIAL_GROUP_LABELS.get(material_group, material_group)
    st.warning(f"No {module_label.lower()} matches are available in the current demo dataset for {material_label}.")
    if note:
        st.caption(note)


def render_reason_list(reasons: list[str]) -> None:
    if reasons:
        st.caption("Why it fits: " + " | ".join(reasons[:4]))


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
        st.dataframe(df, use_container_width=True, height=450)


def build_common_inputs() -> dict[str, Any]:
    st.subheader("Machining Conditions")
    c1, c2, c3 = st.columns(3)
    with c1:
        material_group = st.selectbox(
            "Material Group",
            MATERIAL_GROUPS,
            index=0,
            format_func=lambda x: MATERIAL_GROUP_LABELS[x],
        )
        application_zone = st.selectbox("Application Zone", APPLICATION_ZONES, index=1)
    with c2:
        interrupted_cut = st.selectbox("Interrupted Cut", INTERRUPTED_CUT, index=0)
        stickout = st.selectbox("Stickout", STICKOUT, index=1)
    with c3:
        workholding = st.selectbox("Workholding", WORKHOLDING, index=0)
        cutting_speed_band = st.selectbox("Cutting Speed Band", CUTTING_SPEED_BAND, index=1)

    c4, c5 = st.columns(2)
    with c4:
        doc_band = st.selectbox("DOC Band", DOC_BAND, index=1)
    with c5:
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
    operation = st.selectbox("Turning Operation", ["Longitudinal turning", "Facing", "Profiling", "Plunging"])
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
        elif common["material_group"] == "M":
            score += match_terms(blob, ["stainless", "m"])
        elif common["material_group"] == "K":
            score += match_terms(blob, ["cast iron", "k"])
        scored.append((score, row, reasons))
    scored.sort(key=lambda x: (-x[0], x[1].get("brand", ""), x[1].get("designation_family", "")))

    st.subheader("Turning Recommendation")
    with st.container(border=True):
        st.markdown(f"### {result['recommendation_title']}")
        st.write(result["recommendation_summary"])
        st.write(result["recommendation_fit_sentence"])
        render_metric_strip(
            [
                ("Toughness", result["required_toughness"]),
                ("Wear", result["required_wear_resistance"]),
                ("Coating", result["preferred_coating"]),
                ("Insert Shape", identity["shape"]),
            ]
        )
        st.caption(
            f"Starting insert direction: {identity['identity_summary']}. "
            f"Chipbreaker bias: {result['chipbreaker_hint']['family']}."
        )
        if result["risk_flags"]:
            st.warning("Watch-outs: " + " | ".join(result["risk_flags"]))

    eq = get_equivalent_bucket(common["material_group"], common["application_zone"])
    grades = get_grade_rows(common["material_group"], common["application_zone"], "turning_insert")
    col1, col2 = st.columns([2, 3])
    with col1:
        st.markdown("#### Grade bucket")
        if eq:
            for cand in eq.get("candidates", [])[:6]:
                st.write(f"- **{cand['brand']}** — {cand['grade']}")
        else:
            st.write("No equivalence bucket found.")
    with col2:
        st.markdown("#### Matching grade records")
        if grades:
            st.dataframe(preferred_frame(grades, ["brand", "grade", "zone", "coating", "tags"]), use_container_width=True, height=220)
        else:
            st.write("No grade rows found.")

    st.markdown("#### Top turning families")
    if not scored:
        render_empty_state("turning", common["material_group"])
        return

    for score, row, reasons in scored[:5]:
        with st.container(border=True):
            st.write(f"**{row.get('brand', '')} — {row.get('series', '')}**")
            st.write(f"Family: {row.get('designation_family', row.get('id', ''))}")
            st.write(f"Fit score: {score}")
            st.write(f"Materials: {compact_list(row.get('materials', {}).get('iso_groups', []))}")
            st.write(f"Chipbreaker: {row.get('geometry', {}).get('chipbreaker', 'Not listed')}")
            st.write(f"Recommended grades: {compact_list(row.get('recommended_grades', []))}")
            render_reason_list(reasons)
            if row.get('notes'):
                st.write(row['notes'])


def recommend_drilling(common: dict[str, Any]) -> None:
    drill_type = st.selectbox("Drill Type", ["Solid Carbide Drill", "Indexable Drill"])
    diameter = st.number_input("Hole Diameter (mm)", min_value=0.5, max_value=80.0, value=12.0, step=0.5)
    ld = st.selectbox("Depth Ratio (L/D)", [1, 2, 3, 4, 5, 8, 10, 12, 15, 20, 25, 30], index=4)
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
                reasons.append("internal coolant")
            if common["finish_priority"] == "HIGH":
                score += 1
                reasons.append("finish-side drilling bias")
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
            if common["doc_band"] == "HEAVY":
                score += 1
                reasons.append("productivity-side DOC bias")
            if diameter >= 20:
                score += 1
                reasons.append("larger-diameter fit")
        if common["material_group"] in row.get("materials", {}).get("iso_groups", []):
            score += 2
            reasons.append(f"{common['material_group']} material coverage")
        if common["workholding"] == "POOR" or common["stickout"] == "LONG":
            score -= 1
            reasons.append("flagged for setup stability review")
        scored.append((score, row, reasons))
    scored.sort(key=lambda x: (-x[0], x[1].get("brand", ""), x[1].get("series", "")))

    st.subheader("Drilling Recommendation")
    st.write(f"Target: **{diameter:.1f} mm**, **{ld}xD**, **{MATERIAL_GROUP_LABELS[common['material_group']]}**")
    st.caption(DRILL_TYPE_HINTS[drill_type])
    if not scored:
        alternate = "Solid Carbide Drill" if drill_type == "Indexable Drill" else "Catalog Data Explorer"
        render_empty_state("drilling", common["material_group"], f"Try {alternate} for this material group in the current demo dataset.")
        return

    for score, row, reasons in scored[:6]:
        with st.container(border=True):
            st.write(f"**{row.get('brand', '')} — {row.get('series', '')}**")
            geom = row.get("geometry", {})
            st.write(f"Type: {row.get('subcategory', row.get('tool_category', 'drill'))}")
            if geom.get("diameter_range_mm"):
                st.write(f"Diameter range: {geom['diameter_range_mm'][0]} to {geom['diameter_range_mm'][1]} mm")
            if geom.get("available_l_d"):
                st.write(f"Available L/D: {geom['available_l_d']}")
            elif geom.get("l_d"):
                st.write(f"L/D: {geom['l_d']}")
            coolant = geom.get("coolant")
            if coolant:
                st.write(f"Coolant: {coolant}")
            grade = row.get("grade_or_coating") or row.get("insert_system", {}).get("grade")
            if grade:
                st.write(f"Grade / coating: {grade}")
            st.write(f"Fit score: {score}")
            render_reason_list(reasons)


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
    else:
        rows = load_json("normalized/milling/indexable_cutters.json") or []
        operation_options = {
            "Facing": ["face_milling", "facing"],
            "Shoulder Milling": ["shoulder_milling"],
            "Plunge Milling": ["plunge_milling", "plunging", "high_feed_milling"],
            "Slotting": ["slotting"],
        }
        operation_label = st.selectbox("Face Mill Operation", list(operation_options.keys()))
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
        if mode == "ENDMILL":
            if strategy in operation_terms:
                score += 5
                reasons.append(f"{operation_label.lower()} strategy match")
            if match_terms(blob, [application.get("materials_focus", "")]):
                score += 1
        else:
            if any(term in operations for term in operation_terms):
                score += 5
                reasons.append(f"{operation_label.lower()} cutter coverage")
        if common["application_zone"] == "TOUGH":
            score += match_terms(blob, ["rough", "heavy", "plunge", "shoulder", "high_feed"])
            if match_terms(blob, ["rough", "heavy", "plunge", "shoulder", "high_feed"]):
                reasons.append("tough-side milling bias")
        elif common["application_zone"] == "WEAR":
            score += match_terms(blob, ["finish", "high velocity", "semi finish", "fine", "surface finish"])
            if match_terms(blob, ["finish", "high velocity", "semi finish", "fine", "surface finish"]):
                reasons.append("finish-side milling bias")
        else:
            score += match_terms(blob, ["general", "facing", "profiling"])
            if match_terms(blob, ["general", "facing", "profiling"]):
                reasons.append("balanced milling bias")
        if common["finish_priority"] == "HIGH":
            score += match_terms(blob, ["finish", "semi_finish", "surface finish"])
        if common["doc_band"] == "HEAVY":
            score += match_terms(blob, ["rough", "high_feed", "shoulder", "plunge"])
        if common["material_group"] in row.get("materials", {}).get("iso_groups", []):
            reasons.append(f"{common['material_group']} material coverage")
        scored.append((score, row, reasons))
    scored.sort(key=lambda x: (-x[0], x[1].get("brand", ""), x[1].get("series", "")))

    title = "Endmill Recommendation" if mode == "ENDMILL" else "Face Mill Recommendation"
    st.subheader(title)
    if not scored:
        render_empty_state(title, common["material_group"], "Use Catalog Data Explorer to show the supported milling families in this demo dataset.")
        return

    for score, row, reasons in scored[:6]:
        with st.container(border=True):
            st.write(f"**{row.get('brand', '')} — {row.get('series', '')}**")
            st.write(f"Category: {row.get('subcategory', row.get('tool_category', 'milling'))}")
            geom = row.get('geometry', {})
            if geom.get('flute_count'):
                st.write(f"Flutes: {geom['flute_count']}")
            if geom.get('cutting_edges_per_insert'):
                st.write(f"Edges / insert: {geom['cutting_edges_per_insert']}")
            app = row.get('application', {})
            if app:
                st.write(f"Application: {format_mapping(app)}")
            st.write(f"Fit score: {score}")
            render_reason_list(reasons)


def recommend_grooving(common: dict[str, Any]) -> None:
    operation_options = {
        "Grooving": ["grooving"],
        "Parting": ["parting", "cutoff"],
        "Face Grooving": ["face_grooving", "face grooving"],
        "Undercutting": ["undercutting"],
    }
    operation_label = st.selectbox("Grooving Operation", list(operation_options.keys()))
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
        if common["application_zone"] == "TOUGH":
            score += match_terms(blob, ["heavy", "wmt", "progroove"])
            if match_terms(blob, ["heavy", "wmt", "progroove"]):
                reasons.append("tough-side grooving bias")
        elif common["application_zone"] == "WEAR":
            score += match_terms(blob, ["topgroove", "precision", "finish"])
            if match_terms(blob, ["topgroove", "precision", "finish"]):
                reasons.append("wear-side grooving bias")
        if row_groups:
            reasons.append(f"{common['material_group']} material coverage")
        scored.append((score, row, reasons))
    scored.sort(key=lambda x: (-x[0], x[1].get('brand', ''), x[1].get('series', '')))
    grades = get_grade_rows(common["material_group"], common["application_zone"], "grooving_insert")
    st.subheader("Grooving Recommendation")
    st.caption("Insert-family records in this demo are mostly material-neutral here, so ISO-group sensitivity comes primarily from the matched grade bucket below.")
    if not scored:
        render_empty_state("grooving", common["material_group"])
        return

    for score, row, reasons in scored[:6]:
        with st.container(border=True):
            st.write(f"**{row.get('brand', '')} — {row.get('series', '')}**")
            st.write(f"Family: {row.get('designation_family', row.get('id', ''))}")
            geom = row.get('geometry', {})
            if geom:
                st.write(f"Geometry: {format_mapping(geom)}")
            st.write(f"Fit score: {score}")
            render_reason_list(reasons)
    with st.expander("Matching grooving grades"):
        if grades:
            st.dataframe(preferred_frame(grades, ["brand", "grade", "zone", "coating", "tags"]), use_container_width=True)
        else:
            st.write("No grooving grade rows found.")


def recommend_threading(common: dict[str, Any]) -> None:
    thread_options = {
        "External Threading": "external_threading",
        "Internal Threading": "internal_threading",
    }
    thread_label = st.selectbox("Threading Type", list(thread_options.keys()))
    thread_type = thread_options[thread_label]
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
    st.subheader("Threading Recommendation")
    if not scored:
        render_empty_state("threading", common["material_group"], "The current threading demo dataset is strongest for P, M, and K materials.")
        return

    for score, row, reasons in scored[:6]:
        with st.container(border=True):
            st.write(f"**{row.get('brand', '')} — {row.get('series', '')}**")
            st.write(f"Family: {row.get('designation_family', row.get('id', ''))}")
            st.write(f"Operations: {compact_list(row.get('application', {}).get('operations', []))}")
            st.write(f"Recommended grades in dataset: {', '.join(row.get('recommended_grades', [])) or 'None listed'}")
            st.write(f"Fit score: {score}")
            render_reason_list(reasons)
    with st.expander("Matching threading grades"):
        if grades:
            st.dataframe(preferred_frame(grades, ["brand", "grade", "zone", "coating", "tags"]), use_container_width=True)
        else:
            st.write("No threading grade rows found.")


def recommend_burnishing() -> None:
    rows = load_json("normalized/burnishing/tools.json") or []
    st.subheader("Burnishing Recommendation")
    st.info("Use this when finish, size control, and surface work-hardening matter more than metal removal.")
    for row in rows[:6]:
        with st.container(border=True):
            st.write(f"**{row.get('brand', '')} — {row.get('series', '')}**")
            st.write(row.get('subcategory', row.get('tool_category', 'burnishing_tool')))
            st.write(f"Application: {format_mapping(row.get('application', {}))}")


def recommend_workholding() -> None:
    rows = load_json("normalized/workholding/chucks.json") or []
    st.subheader("Workholding Reference")
    st.info("Use this module to explain setup stability and quick-change capability during the demo.")
    for row in rows[:6]:
        with st.container(border=True):
            st.write(f"**{row.get('brand', '')} — {row.get('series', '')}**")
            st.write(f"Designation: {row.get('designation', row.get('id', ''))}")
            st.write(f"Performance profile: {format_mapping(row.get('performance_profile', {}))}")


st.set_page_config(page_title="CNC Tooling Decision Engine", layout="wide")
st.title("CNC Tooling Decision Engine")
st.caption("Catalog-backed family selection and grade-behavior guidance for turning, drilling, milling, grooving, and threading demos.")
st.info("Demo note: this app is built to recommend credible tool families and grade direction. It is not a full SKU-complete selector.")

mode = st.radio("Mode", ["Decision Engine", "Catalog Data Explorer"], horizontal=True)
if mode == "Catalog Data Explorer":
    render_catalog_explorer()
    st.stop()

family = st.selectbox("Module", list(FAMILY_LABELS.keys()), format_func=lambda x: FAMILY_LABELS[x])
st.caption(MODULE_DESCRIPTIONS[family])

if family in {"BURNISHING", "WORKHOLDING"}:
    if family == "BURNISHING":
        recommend_burnishing()
    else:
        recommend_workholding()
    st.stop()

common = build_common_inputs()
with st.expander("Recommendation Basis", expanded=True):
    behavior = resolve_grade_behavior(common)
    render_metric_strip([
        ("Zone", common["application_zone"]),
        ("Toughness", behavior["required_toughness"]),
        ("Wear", behavior["required_wear_resistance"]),
        ("Coating", behavior["preferred_coating"]),
    ])
    st.write("These selected conditions steer the engine toward a starting family, coating direction, and insert behavior before the catalog shortlist is ranked.")
    st.write(behavior["recommendation_summary"])
    st.write(behavior["recommendation_fit_sentence"])
    st.caption(
        f"Chipbreaker direction: {behavior['chipbreaker_hint']['family']} | "
        f"Geometry direction: {behavior['geometry_hint']['geometry']} | "
        f"Starting identity: {behavior['insert_identity']['identity_summary']}"
    )
    if behavior["risk_flags"]:
        st.warning("Setup watch-outs: " + " | ".join(behavior["risk_flags"]))

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
