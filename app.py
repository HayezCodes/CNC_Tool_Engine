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
from grade_engine.tooling_advisor import TOOL_FAMILY_LABELS, resolve_tooling_recommendation

MATERIAL_GROUP_LABELS = {
    "P": "P - Steel",
    "M": "M - Stainless",
    "K": "K - Cast Iron",
    "N": "N - Non-Ferrous",
    "S": "S - Super Alloy",
    "H": "H - Hardened",
}


def render_supplier_matches(matches: dict) -> None:
    st.subheader("Supplier Search")
    for supplier, data in matches.items():
        with st.container(border=True):
            st.markdown(f"**{supplier}**")
            st.write(f"Recommended Start: {data['recommended_grade']}")
            st.write(f"Fallback: {data['fallback_grade']}")
            st.write(f"Description: {data['description']}")
            links = data.get("links", {})
            if links.get("Search"):
                st.link_button(f"Search {supplier}", links["Search"])


st.set_page_config(page_title="CNC Tool Engine", layout="wide")
st.title("CNC Tool Engine")
st.caption("Shop-floor starter recommendations across turning, grooving, threading, drilling, milling, tapping, and reaming.")

tool_family = st.selectbox(
    "Tool Family",
    TOOL_FAMILIES,
    index=0,
    format_func=lambda item: TOOL_FAMILY_LABELS[item],
)

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

show_internal = st.checkbox("Show internal logic key", value=False)

if st.button("Build Recommendation", type="primary"):
    input_data = {
        "material_group": material_group,
        "application_zone": application_zone,
        "interrupted_cut": interrupted_cut,
        "stickout": stickout,
        "workholding": workholding,
        "cutting_speed_band": cutting_speed_band,
        "doc_band": doc_band,
        "finish_priority": finish_priority,
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
