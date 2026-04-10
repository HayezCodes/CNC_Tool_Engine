import streamlit as st
from grade_engine.enums import (
    TOOL_FAMILIES, MATERIAL_GROUPS, APPLICATION_ZONES, INTERRUPTED_CUT, STICKOUT,
    WORKHOLDING, CUTTING_SPEED_BAND, DOC_BAND, FINISH_PRIORITY
)
from grade_engine.engine import resolve_grade_behavior
from grade_engine.resolver import map_behavior_to_supplier_grades
from grade_engine.router import get_tool_family_message

MATERIAL_GROUP_LABELS = {
    "P": "P — Steel",
    "M": "M — Stainless",
    "K": "K — Cast Iron",
    "N": "N — Non-Ferrous",
    "S": "S — Super Alloy",
    "H": "H — Hardened",
}

st.set_page_config(page_title="Universal Tooling Engine V2", layout="wide")
st.title("Universal Tooling Engine V2")
st.caption("Tool-family router + expanded material groups")

tool_family = st.selectbox("Tool Family", TOOL_FAMILIES, index=0)
family_info = get_tool_family_message(tool_family)

with st.container(border=True):
    st.markdown(f"### {family_info['title']}")
    st.write(family_info["message"])

if tool_family != "TURNING_INSERT":
    st.info("This family is routed and ready for future logic, but the active engine is still turning inserts.")
    st.stop()

col1, col2, col3 = st.columns(3)
with col1:
    material_group = st.selectbox(
        "Material Group",
        MATERIAL_GROUPS,
        index=0,
        format_func=lambda x: MATERIAL_GROUP_LABELS[x],
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

if st.button("Resolve Grade Behavior", type="primary"):
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

    result = resolve_grade_behavior(input_data)
    supplier_matches = map_behavior_to_supplier_grades(
        result["material_group"], result["application_zone"], result["preferred_coating"],
        result["geometry_hint"], result["chipbreaker_hint"], result.get("insert_identity"),
    )

    st.subheader("Recommendation")
    with st.container(border=True):
        st.markdown(f"### {result['recommendation_title']}")
        st.write(result["recommendation_summary"])
        st.write(result["recommendation_fit_sentence"])

    a, b, c = st.columns(3)
    a.metric("Required Toughness", result["required_toughness"])
    b.metric("Required Wear Resistance", result["required_wear_resistance"])
    c.metric("Preferred Coating", result["preferred_coating"])

    st.subheader("What that means")
    st.write(f"**Toughness:** {result['toughness_explained']}")
    st.write(f"**Wear resistance:** {result['wear_explained']}")
    st.write(f"**Coating:** {result['coating_explained']}")

    g1, g2 = st.columns(2)
    with g1:
        st.subheader("Starter geometry direction")
        st.info(f"**{result['geometry_hint']['geometry']}**\n\n{result['geometry_hint']['why']}")
    with g2:
        st.subheader("Starter chipbreaker direction")
        st.info(f"**{result['chipbreaker_hint']['family']}**\n\n{result['chipbreaker_hint']['why']}")

    insert_identity = result.get("insert_identity", {})
    if insert_identity:
        st.subheader("Starter Insert Identity")
        i1, i2, i3, i4 = st.columns(4)
        i1.metric("Shape", insert_identity.get("shape", "-"))
        i2.metric("ANSI Size", insert_identity.get("ansi_size", "-"))
        i3.metric("ISO Size", insert_identity.get("iso_size", "-"))
        i4.metric("Nose Radius", insert_identity.get("nose_radius", "-"))
        st.info(insert_identity.get("identity_summary", ""))

    if show_internal:
        st.caption("Internal logic key")
        st.code(result["grade_behavior_key"], language="text")

    st.subheader("Why this was chosen")
    for step in result["explanation_steps"]:
        st.write(f"- {step}")

    st.subheader("What to watch")
    if result["risk_flags"]:
        for risk in result["risk_flags"]:
            st.warning(risk)
    else:
        st.success("No major risk flags from the current input mix.")

    st.subheader("Supplier Matches")
    for supplier, data in supplier_matches.items():
        with st.container(border=True):
            st.markdown(f"**{supplier}**")
            st.write(f"Recommended Grade: {data['recommended_grade']}")
            st.write(f"Fallback Grade: {data['fallback_grade']}")
            st.write(f"Description: {data['description']}")
            links = data.get("links", {})
            if links:
                search_url = links.get("Search")
                if search_url:
                    st.link_button(f"Search {supplier}", search_url)
