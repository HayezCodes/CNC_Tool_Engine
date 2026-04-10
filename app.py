import streamlit as st

from grade_engine.enums import (
    APPLICATION_ZONES,
    CUTTING_SPEED_BAND,
    DOC_BAND,
    FINISH_PRIORITY,
    INTERRUPTED_CUT,
    MATERIAL_GROUPS,
    STICKOUT,
    TOOL_FAMILIES,
    WORKHOLDING,
)
from grade_engine.router import get_tool_family_message
from grade_engine.tooling_advisor import TOOL_FAMILY_LABELS, resolve_tooling_recommendation

MATERIAL_GROUP_LABELS = {
    "P": "P - Steel",
    "M": "M - Stainless",
    "K": "K - Cast Iron",
    "N": "N - Non-Ferrous",
    "S": "S - Super Alloy",
    "H": "H - Hardened",
}


THREAD_PROFILE_OPTIONS = {
    "UNIFIED_60": "60 degree UN / ISO",
    "WHITWORTH_55": "55 degree Whitworth",
    "ACME_29": "29 degree Acme / Trapezoidal",
}

THREAD_SIDE_OPTIONS = {
    "EXTERNAL": "External",
    "INTERNAL": "Internal",
}

HOLE_TYPE_OPTIONS = {
    "THROUGH": "Through Hole",
    "BLIND": "Blind Hole",
}


def render_supplier_matches(matches: dict) -> None:
    st.subheader("Supplier Search")
    for supplier, data in matches.items():
        with st.container(border=True):
            st.markdown(f"**{supplier}**")
            recommended_label = data.get("recommended_label", "Recommended Grade")
            fallback_label = data.get("fallback_label", "Fallback Grade")
            st.write(f"{recommended_label}: {data['recommended_grade']}")
            st.write(f"{fallback_label}: {data['fallback_grade']}")
            st.write(f"Description: {data['description']}")
            if data.get("search_query"):
                st.code(data["search_query"], language="text")
            links = data.get("links", {})
            if links.get("Search"):
                st.link_button(f"Search {supplier}", links["Search"])


def collect_process_specific_inputs(tool_family: str) -> dict:
    extra_inputs = {}

    if tool_family == "THREADING_INSERT":
        col_a, col_b = st.columns(2)
        with col_a:
            extra_inputs["thread_profile"] = st.selectbox(
                "Thread Profile",
                list(THREAD_PROFILE_OPTIONS),
                index=0,
                format_func=lambda item: THREAD_PROFILE_OPTIONS[item],
            )
        with col_b:
            extra_inputs["thread_side"] = st.selectbox(
                "Thread Orientation",
                list(THREAD_SIDE_OPTIONS),
                index=0,
                format_func=lambda item: THREAD_SIDE_OPTIONS[item],
            )

    if tool_family in {"TAP", "REAMER"}:
        extra_inputs["hole_type"] = st.selectbox(
            "Hole Type",
            list(HOLE_TYPE_OPTIONS),
            index=0,
            format_func=lambda item: HOLE_TYPE_OPTIONS[item],
        )

    return extra_inputs


st.set_page_config(page_title="CNC Tool Engine", layout="wide")
st.title("CNC Tool Engine")
st.caption("Shop-floor starter recommendations across turning, grooving, threading, drilling, milling, tapping, and reaming.")

tool_family = st.selectbox(
    "Tool Family",
    TOOL_FAMILIES,
    index=0,
    format_func=lambda item: TOOL_FAMILY_LABELS[item],
)
family_info = get_tool_family_message(tool_family)

with st.container(border=True):
    st.markdown(f"### {family_info['title']}")
    st.write(family_info["message"])

col1, col2, col3 = st.columns(3)
with col1:
    material_group = st.selectbox(
        "Material Group",
        MATERIAL_GROUPS,
        index=0,
        format_func=lambda item: MATERIAL_GROUP_LABELS[item],
    )
    application_zone = st.selectbox("Application Zone", APPLICATION_ZONES, index=1)
with col2:
    interrupted_cut = st.selectbox("Interrupted Cut", INTERRUPTED_CUT, index=0)
    stickout = st.selectbox("Stickout", STICKOUT, index=1)
with col3:
    workholding = st.selectbox("Workholding", WORKHOLDING, index=0)
    cutting_speed_band = st.selectbox("Cutting Speed Band", CUTTING_SPEED_BAND, index=1)

col4, col5 = st.columns(2)
with col4:
    doc_band = st.selectbox("DOC Band", DOC_BAND, index=1)
with col5:
    finish_priority = st.selectbox("Finish Priority", FINISH_PRIORITY, index=1)

extra_inputs = collect_process_specific_inputs(tool_family)

show_internal = st.checkbox("Show internal logic key", value=False)
st.caption("Recommendations update automatically as inputs change.")

input_data = {
    "material_group": material_group,
    "application_zone": application_zone,
    "interrupted_cut": interrupted_cut,
    "stickout": stickout,
    "workholding": workholding,
    "cutting_speed_band": cutting_speed_band,
    "doc_band": doc_band,
    "finish_priority": finish_priority,
    **extra_inputs,
}

recommendation = resolve_tooling_recommendation(tool_family, input_data)
behavior = recommendation["behavior"]

st.subheader("Recommendation")
with st.container(border=True):
    st.markdown(f"### {behavior['recommendation_title']}")
    st.write(behavior["recommendation_summary"])
    st.write(behavior["recommendation_fit_sentence"])

a, b, c = st.columns(3)
a.metric("Required Toughness", behavior["required_toughness"])
b.metric("Required Wear Resistance", behavior["required_wear_resistance"])
c.metric("Preferred Coating", behavior["preferred_coating"])

st.subheader("Starter Setup")
s1, s2, s3 = st.columns(3)
s1.info(f"**Start with**\n\n{recommendation['starter_platform']}")
s2.info(f"**Geometry / style**\n\n{recommendation['geometry_focus']}")
s3.info(f"**Holder / setup**\n\n{recommendation['holder_focus']}")

if tool_family == "TURNING_INSERT":
    st.subheader("Turning Insert Identity")
    insert_identity = behavior["insert_identity"]
    i1, i2, i3, i4 = st.columns(4)
    i1.metric("Shape", insert_identity.get("shape", "-"))
    i2.metric("ANSI Size", insert_identity.get("ansi_size", "-"))
    i3.metric("ISO Size", insert_identity.get("iso_size", "-"))
    i4.metric("Nose Radius", insert_identity.get("nose_radius", "-"))
    st.info(insert_identity.get("identity_summary", ""))

st.subheader("Why this was chosen")
for step in recommendation["process_notes"]:
    st.write(f"- {step}")

st.subheader("What to watch")
if recommendation["watch_items"]:
    for item in recommendation["watch_items"]:
        st.warning(item)
else:
    st.success("No major watch items from the current input mix.")

st.subheader("Behavior Readout")
st.write(f"**Toughness:** {behavior['toughness_explained']}")
st.write(f"**Wear resistance:** {behavior['wear_explained']}")
st.write(f"**Coating:** {behavior['coating_explained']}")

if show_internal:
    st.caption("Internal logic key")
    st.code(behavior["grade_behavior_key"], language="text")

render_supplier_matches(recommendation["supplier_matches"])
