from __future__ import annotations

from functools import lru_cache
from typing import Any

from grade_engine.catalog_review import load_reviewed_catalog_records


VERIFICATION_NOTE = (
    "Reviewed catalog-family records are family-level guidance only and do not replace manufacturer cutting data."
)

OPERATION_RELATED_GROUPS = {
    "general_milling": {"general_milling", "slotting", "profiling", "roughing", "finishing", "shoulder_milling"},
    "dynamic_milling": {"dynamic_milling", "adaptive_milling", "roughing", "profiling", "high_feed_milling"},
    "aluminum_milling": {"aluminum_milling", "general_milling", "profiling", "finishing"},
    "specialty": {"specialty", "specialty_milling", "feature_milling", "undercutting", "problem_solving"},
    "chamfer": {"chamfer", "deburring", "edge_breaking", "spotting"},
    "keyseat": {"keyseat", "keyway", "slotting", "undercutting"},
    "threading": {"threading", "thread_milling", "internal_threading", "external_threading"},
    "small_bore": {
        "small_bore",
        "small_id_turning",
        "internal_turning",
        "small_feature_turning",
        "internal_grooving",
        "internal_threading",
        "boring",
    },
    "turning": {"turning", "external_turning", "internal_turning", "facing", "profiling"},
    "production_turning": {
        "production_turning",
        "external_turning",
        "internal_turning",
        "roughing",
        "finishing",
        "facing",
        "profiling",
        "grooving",
        "threading",
    },
    "grooving": {"grooving", "internal_grooving", "face_grooving", "parting"},
    "drilling": {"drilling", "through_hole_drilling", "blind_hole_drilling", "high_efficiency_drilling"},
}

OPERATION_GEOMETRY_HINTS = {
    "dynamic_milling": {"dynamic_milling", "adaptive_milling", "variable_pitch", "variable_helix"},
    "aluminum_milling": {"aluminum_geometry", "high_rake_candidate", "chip_evacuation_candidate"},
    "chamfer": {"chamfer_mill"},
    "keyseat": {"keyseat_cutter"},
    "specialty": {"specialty_milling", "undercut_tool", "specialty_turning"},
    "small_bore": {"small_id_candidate", "miniature_turning", "internal_grooving", "internal_threading"},
    "production_turning": {"turning_insert", "grooving_insert", "threading_insert", "indexable_cutter"},
    "grooving": {"grooving_insert", "grooving_toolholder", "internal_grooving"},
    "threading": {"threading_insert", "threading_toolholder", "thread_mill", "internal_threading"},
}

OPERATION_FAMILY_HINTS = {
    "general_milling": {"endmill", "general_purpose", "production_milling"},
    "dynamic_milling": {"endmill", "dynamic", "adaptive", "high_performance"},
    "aluminum_milling": {"endmill", "aluminum", "high_efficiency"},
    "specialty": {"specialty", "miniature", "problem_solving"},
    "chamfer": {"chamfer_mill", "specialty"},
    "keyseat": {"keyseat_cutter", "specialty"},
    "threading": {"thread_mill", "threading_insert", "threading_tool", "threading_toolholder"},
    "small_bore": {"boring_bar", "miniature", "small_bore", "grooving_tool", "threading_tool"},
    "turning": {"turning_insert", "boring_bar", "grooving_tool", "threading_tool"},
    "production_turning": {"turning_insert", "milling_insert", "grooving_insert", "threading_insert", "indexable_cutter"},
    "grooving": {"grooving_insert", "grooving_toolholder", "grooving_tool"},
    "drilling": {"drill", "general_purpose", "high_performance"},
}

OPERATION_TOOL_CATEGORIES = {
    "general_milling": {"endmill", "chamfer_mill", "specialty_milling"},
    "dynamic_milling": {"endmill"},
    "aluminum_milling": {"endmill"},
    "specialty": {"specialty_milling", "undercut_tool", "miniature_endmill", "thread_mill", "keyseat_cutter", "chamfer_mill"},
    "chamfer": {"chamfer_mill"},
    "keyseat": {"keyseat_cutter"},
    "threading": {"thread_mill", "threading_insert", "threading_tool", "threading_toolholder"},
    "small_bore": {"boring_bar", "miniature_turning_tool", "grooving_tool", "threading_tool", "specialty_turning"},
    "turning": {"turning_insert", "boring_bar", "grooving_tool", "threading_tool"},
    "production_turning": {"turning_insert", "milling_insert", "grooving_insert", "threading_insert", "indexable_cutter", "grooving_toolholder", "threading_toolholder", "boring_bar"},
    "grooving": {"grooving_insert", "grooving_tool", "grooving_toolholder"},
    "drilling": {"drill", "tap"},
}

STRATEGY_HINTS = {
    "balanced": set(),
    "value": {"value", "general_purpose", "job_shop_general", "value_focused"},
    "high_performance": {"high_performance", "high_efficiency", "production_milling", "dynamic", "adaptive"},
    "specialty": {"specialty_feature", "manual_catalog_review_required", "miniature_work", "problem_solving"},
    "production_turning": {"production_turning", "production_milling", "indexable_turning", "tooling_system"},
    "small_bore": {"small_id_access", "small_feature_access", "miniature_work"},
    "dynamic": {"dynamic", "adaptive", "high_efficiency", "radial_engagement_strategy"},
    "adaptive": {"dynamic", "adaptive", "high_efficiency", "radial_engagement_strategy"},
}

PROBLEM_TYPE_HINTS = {
    "dynamic_milling": {"dynamic_milling", "adaptive_milling", "high_efficiency", "dynamic", "adaptive"},
    "specialty_feature": {"specialty_feature", "problem_solving", "miniature_work"},
    "small_bore_access": {"small_id_access", "small_feature_access", "small_id_candidate", "miniature"},
    "production_turning": {"production_turning", "indexable_turning", "tooling_system"},
    "needs_value_option": {"value", "value_focused", "general_purpose"},
    "chip_control": {"chip_evacuation_candidate", "grooving", "groove_form_requires_review"},
    "poor_finish": {"finishing", "surface_finish_priority", "contouring_candidate"},
    "chatter": {"chatter_reduction_candidate", "variable_pitch", "variable_helix", "edge_strength_candidate"},
    "short_tool_life": {"edge_strength_priority", "production_stability", "high_performance"},
}


@lru_cache(maxsize=1)
def load_reviewed_family_boost_data() -> list[dict[str, Any]]:
    normalized_records: list[dict[str, Any]] = []
    for record in load_reviewed_catalog_records():
        family_types = _derive_family_types(record)
        normalized_records.append(
            {
                "brand": record.get("brand", ""),
                "family_name": record.get("family_name", ""),
                "tool_category": _normalize(record.get("tool_category", "")),
                "operation_fit": {_normalize(value) for value in record.get("operation_fit", [])},
                "material_fit": {str(value).strip().upper() for value in record.get("material_fit", [])},
                "strategy_fit": {_normalize(value) for value in record.get("strategy_fit", [])},
                "geometry_tags": {_normalize(value) for value in record.get("geometry_tags", [])},
                "family_type": family_types,
            }
        )
    return normalized_records


def calculate_reviewed_family_boost(
    operation: str,
    material_group: str,
    strategy: str | None = None,
    problem_type: str | None = None,
) -> dict[str, Any]:
    operation_key = _normalize(operation)
    material_key = str(material_group).strip().upper()
    strategy_key = _normalize(strategy) if strategy else ""
    problem_key = _normalize(problem_type) if problem_type else ""

    target_geometry = set(OPERATION_GEOMETRY_HINTS.get(operation_key, set()))
    target_family_types = set(OPERATION_FAMILY_HINTS.get(operation_key, set()))
    target_strategy_tags = set(STRATEGY_HINTS.get(strategy_key, set()))
    target_problem_tags = set(PROBLEM_TYPE_HINTS.get(problem_key, set()))
    related_operations = set(OPERATION_RELATED_GROUPS.get(operation_key, set()))
    target_tool_categories = set(OPERATION_TOOL_CATEGORIES.get(operation_key, set()))

    brand_support: dict[str, dict[str, Any]] = {}
    for record in load_reviewed_family_boost_data():
        record_score = 0
        reasons: list[str] = []
        category_is_relevant = not target_tool_categories or record["tool_category"] in target_tool_categories

        if category_is_relevant and record["tool_category"]:
            record_score += 3
            reasons.append(f"reviewed {_friendly_label(record['tool_category'])} family coverage")

        if operation_key and operation_key in record["operation_fit"]:
            record_score += 6
            reasons.append(f"{_friendly_operation(operation_key)} family match")
        elif category_is_relevant and related_operations and record["operation_fit"].intersection(related_operations):
            record_score += 3
            reasons.append(f"related {_friendly_operation(operation_key)} family coverage")

        if material_key and material_key in record["material_fit"]:
            record_score += 4
            reasons.append(f"{material_key} material support")

        if strategy_key and strategy_key in record["strategy_fit"]:
            record_score += 4
            reasons.append(f"{_friendly_label(strategy_key)} strategy support")
        elif target_strategy_tags and record["strategy_fit"].intersection(target_strategy_tags):
            record_score += 2
            reasons.append(f"reviewed {_friendly_label(strategy_key)} family coverage")

        geometry_matches = sorted(record["geometry_tags"].intersection(target_geometry | target_problem_tags))
        if geometry_matches:
            record_score += min(4, len(geometry_matches) * 2)
            reasons.append(f"{_friendly_label(geometry_matches[0])} geometry match")

        family_type_matches = sorted(record["family_type"].intersection(target_family_types | target_problem_tags))
        if family_type_matches:
            record_score += min(4, len(family_type_matches) * 2)
            reasons.append(f"reviewed {_friendly_label(family_type_matches[0])} family coverage")

        if problem_key and category_is_relevant and (
            record["strategy_fit"].intersection(target_problem_tags) or record["family_type"].intersection(target_problem_tags)
        ):
            record_score += 2
            reasons.append(f"{_friendly_label(problem_key)} problem-fit family coverage")

        if record_score <= 0:
            continue

        brand_entry = brand_support.setdefault(
            record["brand"],
            {
                "brand": record["brand"],
                "boost_score": 0,
                "matched_reasons": [],
                "supporting_families": [],
                "record_scores": [],
            },
        )
        brand_entry["record_scores"].append(record_score)
        for reason in reasons:
            if reason not in brand_entry["matched_reasons"]:
                brand_entry["matched_reasons"].append(reason)
        if record["family_name"] and record["family_name"] not in brand_entry["supporting_families"]:
            brand_entry["supporting_families"].append(record["family_name"])

    brand_boosts = []
    for entry in brand_support.values():
        score_parts = sorted(entry.pop("record_scores"), reverse=True)
        aggregate_score = 0
        if score_parts:
            aggregate_score += score_parts[0]
        if len(score_parts) > 1:
            aggregate_score += score_parts[1] // 2
        if len(score_parts) > 2:
            aggregate_score += score_parts[2] // 4
        entry["boost_score"] = min(aggregate_score, 24)
        entry["matched_reasons"] = entry["matched_reasons"][:6]
        entry["supporting_families"] = entry["supporting_families"][:4]
        entry["confidence_level"] = _confidence_level(entry["boost_score"])
        brand_boosts.append(entry)

    brand_boosts.sort(key=lambda item: (-item["boost_score"], item["brand"]))
    return {
        "brand_boosts": brand_boosts,
        "verification_note": VERIFICATION_NOTE,
    }


def merge_reviewed_boosts_into_recommendations(
    base_recommendations: list[dict],
    reviewed_boosts: dict,
) -> list[dict]:
    boost_map = {
        item.get("brand"): item
        for item in reviewed_boosts.get("brand_boosts", [])
        if item.get("brand")
    }

    merged: list[dict[str, Any]] = []
    for recommendation in base_recommendations:
        item = dict(recommendation)
        support = boost_map.get(item.get("brand"))
        item["reviewed_catalog_verification_note"] = reviewed_boosts.get("verification_note", VERIFICATION_NOTE)

        if support:
            ranking_adjustment = min(3, max(1, support["boost_score"] // 6))
            item["score"] = item.get("score", 0) + ranking_adjustment
            existing_reasons = list(item.get("reasons", []))
            support_reason = (
                "Reviewed catalog support: "
                + ", ".join(reason for reason in support.get("matched_reasons", [])[:2])
            )
            if support_reason not in existing_reasons:
                existing_reasons.append(support_reason)
            item["reasons"] = existing_reasons
            item["reviewed_catalog_support"] = {
                "boost_score": support["boost_score"],
                "ranking_adjustment": ranking_adjustment,
                "matched_reasons": list(support.get("matched_reasons", [])),
                "supporting_families": list(support.get("supporting_families", [])),
                "confidence_level": support.get("confidence_level", "light_family_match"),
            }

        merged.append(item)

    return sorted(merged, key=lambda item: (-item.get("score", 0), item.get("brand", "")))


def _derive_family_types(record: dict[str, Any]) -> set[str]:
    family_types = {_normalize(record.get("tool_category", ""))}
    family_name = _normalize(record.get("family_name", ""))
    strategy_fit = {_normalize(value) for value in record.get("strategy_fit", [])}
    geometry_tags = {_normalize(value) for value in record.get("geometry_tags", [])}
    family_types.update(strategy_fit)
    family_types.update(geometry_tags)

    keyword_pairs = {
        "general_purpose": ["general_purpose", "general"],
        "value": ["value"],
        "high_performance": ["high_performance"],
        "dynamic": ["dynamic"],
        "adaptive": ["adaptive"],
        "production_milling": ["production"],
        "endmill": ["end_mill", "endmill"],
        "chamfer_mill": ["chamfer"],
        "keyseat_cutter": ["keyseat"],
        "thread_mill": ["thread_mill", "threading"],
        "miniature": ["miniature"],
        "boring_bar": ["boring_bar", "small_id"],
        "grooving_insert": ["grooving", "parting"],
        "threading_insert": ["threading_insert"],
        "turning_insert": ["turning_insert"],
        "milling_insert": ["milling_insert"],
        "indexable_cutter": ["high_feed", "indexable", "cutter_system"],
        "multifunction": ["multifunction"],
        "specialty": ["specialty", "undercut"],
        "small_bore": ["small_id", "small_bore"],
        "drill": ["drill"],
        "tap": ["tap"],
    }
    for family_type, terms in keyword_pairs.items():
        if any(term in family_name for term in terms):
            family_types.add(family_type)

    return {value for value in family_types if value}


def _confidence_level(boost_score: int) -> str:
    if boost_score >= 16:
        return "high_family_match"
    if boost_score >= 9:
        return "medium_family_match"
    return "light_family_match"


def _friendly_operation(value: str) -> str:
    if value == "dynamic_milling":
        return "dynamic/adaptive milling"
    if value == "small_bore":
        return "small-bore"
    if value == "production_turning":
        return "production turning"
    return _friendly_label(value)


def _friendly_label(value: str) -> str:
    return value.replace("_", " ")


def _normalize(value: object) -> str:
    return str(value).strip().lower().replace(" ", "_").replace("-", "_")
