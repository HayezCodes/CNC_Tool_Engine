import json
from pathlib import Path
from typing import Any


DEFAULT_DATA_ROOT = Path(__file__).resolve().parent.parent / "tool_data"
BRAND_DATA_PATH = Path("brand_intelligence") / "tool_brands.json"
ENDMILL_DATA_PATH = Path("brand_intelligence") / "endmill_families.json"
INSERT_GRADE_DATA_PATH = Path("brand_intelligence") / "insert_grade_families.json"

PRIORITY_TERMS = {
    "balanced": [],
    "value": ["value", "budget", "value alternative", "cost effective", "easy sourcing", "job shop"],
    "high_performance": ["high_performance", "high performance", "dynamic milling", "production milling"],
    "specialty": ["specialty", "miniature", "problem solving", "keyseat", "chamfer", "undercutting"],
    "production_turning": ["production_turning", "production turning", "turning_inserts", "indexable"],
    "small_bore": ["small_bore", "small bore", "miniature", "boring_bars", "small_id_work"],
}

STRATEGY_TERMS = {
    "balanced": [],
    "adaptive": ["adaptive", "dynamic", "high_efficiency", "light_adaptive"],
    "dynamic": ["adaptive", "dynamic", "high_efficiency"],
    "conventional": ["conventional", "job_shop_general"],
    "value": ["value", "job_shop_general", "easy_sourcing"],
    "specialty": ["specialty_feature", "miniature_work", "problem_solving"],
}


def load_brand_intelligence(data_root: Path | None = None) -> list[dict]:
    return _load_records(BRAND_DATA_PATH, data_root, "Brand intelligence")


def load_endmill_families(data_root: Path | None = None) -> list[dict]:
    return _load_records(ENDMILL_DATA_PATH, data_root, "Endmill family")


def load_insert_grade_families(data_root: Path | None = None) -> list[dict]:
    return _load_records(INSERT_GRADE_DATA_PATH, data_root, "Insert grade family")


def get_brand_names() -> list[str]:
    return sorted(record["brand"] for record in load_brand_intelligence() if record.get("brand"))


def filter_brands_by_operation(operation: str) -> list[dict]:
    operation_key = _normalize(operation)
    return [
        record
        for record in load_brand_intelligence()
        if operation_key in {_normalize(item) for item in record.get("best_fit_operations", [])}
    ]


def filter_brands_by_material(material_group: str) -> list[dict]:
    material_key = material_group.strip().upper()
    return [
        record
        for record in load_brand_intelligence()
        if material_key in {str(item).strip().upper() for item in record.get("material_strengths", [])}
    ]


def recommend_brand_families(
    operation: str,
    material_group: str,
    priority: str = "balanced",
) -> list[dict]:
    priority_key = _normalize(priority)
    if priority_key not in PRIORITY_TERMS:
        priority_key = "balanced"

    operation_key = _normalize(operation)
    material_key = material_group.strip().upper()
    recommendations: list[dict[str, Any]] = []

    for record in load_brand_intelligence():
        score = 0
        reasons: list[str] = []
        operations = {_normalize(item) for item in record.get("best_fit_operations", [])}
        materials = {str(item).strip().upper() for item in record.get("material_strengths", [])}

        if operation_key in operations:
            score += 4
            reasons.append(f"Supports {operation_key} at the family-guidance level.")
        elif _operation_family_match(operation_key, operations):
            score += 2
            reasons.append(f"Related operation fit for {operation_key}.")

        if material_key in materials:
            score += 3
            reasons.append(f"Listed as a practical candidate for ISO {material_key} material work.")

        priority_score, priority_reasons = _score_priority(record, priority_key)
        score += priority_score
        reasons.extend(priority_reasons)

        if priority_key == "balanced" and score > 0:
            score += 1
            reasons.append("Balanced priority keeps broad practical shop coverage in play.")

        if score > 0:
            recommendations.append(
                {
                    "brand": record["brand"],
                    "score": score,
                    "reasons": reasons,
                    "shop_use_notes": record.get("shop_use_notes", []),
                    "source_status": record.get("source_status", "unknown"),
                    "brand_type": record.get("brand_type", []),
                    "best_fit_operations": record.get("best_fit_operations", []),
                    "material_strengths": record.get("material_strengths", []),
                    "recommended_engine_use": record.get("recommended_engine_use", []),
                    "official_source_label": record.get("official_source_label", ""),
                    "official_source_url": record.get("official_source_url", ""),
                    "verification_level": record.get("verification_level", ""),
                }
            )

    return sorted(recommendations, key=lambda item: (-item["score"], item["brand"]))


def recommend_endmill_families(
    operation: str,
    material_group: str,
    strategy: str = "balanced",
    priority: str = "balanced",
) -> list[dict]:
    operation_key = _normalize(operation)
    material_key = material_group.strip().upper()
    strategy_key = _normalize(strategy)
    priority_key = _normalize(priority)
    if strategy_key not in STRATEGY_TERMS:
        strategy_key = "balanced"
    if priority_key not in PRIORITY_TERMS:
        priority_key = "balanced"

    recommendations: list[dict[str, Any]] = []
    for record in load_endmill_families():
        score = 0
        reasons: list[str] = []
        operations = {_normalize(item) for item in record.get("operation_fit", [])}
        materials = {str(item).strip().upper() for item in record.get("material_fit", [])}

        if operation_key in operations:
            score += 4
            reasons.append(f"Endmill family supports {operation_key}.")
        elif _operation_family_match(operation_key, operations):
            score += 2
            reasons.append(f"Related endmill operation fit for {operation_key}.")

        if material_key in materials:
            score += 3
            reasons.append(f"Family is a practical ISO {material_key} candidate.")

        strategy_score, strategy_reasons = _score_terms(
            record,
            STRATEGY_TERMS[strategy_key],
            f"{strategy_key.replace('_', ' ')} strategy",
            ["family_type", "strategy_fit", "strengths", "operation_fit"],
        )
        priority_score, priority_reasons = _score_terms(
            record,
            PRIORITY_TERMS[priority_key],
            f"{priority_key.replace('_', ' ')} priority",
            ["family_type", "strategy_fit", "strengths", "operation_fit"],
        )
        score += strategy_score + priority_score
        reasons.extend(strategy_reasons)
        reasons.extend(priority_reasons)

        if priority_key == "balanced" and strategy_key == "balanced" and score > 0:
            score += 1
            reasons.append("Balanced selection keeps broad shop-fit endmill families in play.")

        if score > 0:
            recommendations.append(
                {
                    "brand": record["brand"],
                    "family_name": record["family_name"],
                    "score": score,
                    "reasons": reasons,
                    "operation_fit": record.get("operation_fit", []),
                    "material_fit": record.get("material_fit", []),
                    "strategy_fit": record.get("strategy_fit", []),
                    "strengths": record.get("strengths", []),
                    "cautions": record.get("cautions", []),
                    "source_status": record.get("source_status", "unknown"),
                    "verification_level": record.get("verification_level", ""),
                }
            )

    return sorted(recommendations, key=lambda item: (-item["score"], item["brand"]))


def recommend_insert_grade_families(
    operation: str,
    material_group: str,
    priority: str = "balanced",
) -> list[dict]:
    operation_key = _normalize(operation)
    material_key = material_group.strip().upper()
    priority_key = _normalize(priority)
    if priority_key not in PRIORITY_TERMS:
        priority_key = "balanced"

    recommendations: list[dict[str, Any]] = []
    for record in load_insert_grade_families():
        score = 0
        reasons: list[str] = []
        applications = {_normalize(item) for item in record.get("application_fit", [])}
        focus = {_normalize(item) for item in record.get("insert_focus", [])}
        materials = {str(item).strip().upper() for item in record.get("material_fit", [])}

        if operation_key in applications or operation_key in focus:
            score += 4
            reasons.append(f"Insert family supports {operation_key}.")
        elif _insert_operation_family_match(operation_key, applications, focus):
            score += 2
            reasons.append(f"Related insert-family fit for {operation_key}.")

        if material_key in materials:
            score += 3
            reasons.append(f"Insert family is a practical ISO {material_key} candidate.")

        priority_score, priority_reasons = _score_terms(
            record,
            PRIORITY_TERMS[priority_key],
            f"{priority_key.replace('_', ' ')} priority",
            ["insert_focus", "application_fit", "grade_behavior_tags", "chipbreaker_behavior_tags"],
        )
        score += priority_score
        reasons.extend(priority_reasons)

        if priority_key == "balanced" and score > 0:
            score += 1
            reasons.append("Balanced selection keeps broad insert-family candidates in play.")

        if score > 0:
            recommendations.append(
                {
                    "brand": record["brand"],
                    "score": score,
                    "reasons": reasons,
                    "insert_focus": record.get("insert_focus", []),
                    "material_fit": record.get("material_fit", []),
                    "application_fit": record.get("application_fit", []),
                    "grade_behavior_tags": record.get("grade_behavior_tags", []),
                    "chipbreaker_behavior_tags": record.get("chipbreaker_behavior_tags", []),
                    "shop_use_notes": record.get("shop_use_notes", []),
                    "source_status": record.get("source_status", "unknown"),
                    "verification_level": record.get("verification_level", ""),
                }
            )

    return sorted(recommendations, key=lambda item: (-item["score"], item["brand"]))


def _score_priority(record: dict, priority: str) -> tuple[int, list[str]]:
    terms = PRIORITY_TERMS.get(priority, [])
    if not terms:
        return 0, []

    searchable = [
        *record.get("brand_type", []),
        *record.get("primary_strengths", []),
        *record.get("recommended_engine_use", []),
        *record.get("best_fit_operations", []),
    ]
    normalized_blob = " ".join(_normalize(item) for item in searchable)
    matched_terms = [term for term in terms if _normalize(term) in normalized_blob]
    if not matched_terms:
        return 0, []

    label = priority.replace("_", " ")
    return 3, [f"Matches {label} priority through {', '.join(sorted(set(matched_terms)))}."]


def _score_terms(record: dict, terms: list[str], label: str, fields: list[str]) -> tuple[int, list[str]]:
    if not terms:
        return 0, []
    searchable: list[str] = []
    for field in fields:
        searchable.extend(record.get(field, []))
    normalized_blob = " ".join(_normalize(item) for item in searchable)
    matched_terms = [term for term in terms if _normalize(term) in normalized_blob]
    if not matched_terms:
        return 0, []
    return 3, [f"Matches {label} through {', '.join(sorted(set(matched_terms)))}."]


def _operation_family_match(operation: str, operations: set[str]) -> bool:
    milling_ops = {"general_milling", "dynamic_milling", "aluminum_milling", "keyseat", "chamfer", "slotting", "profiling", "specialty"}
    turning_ops = {"turning", "production_turning", "grooving", "small_bore"}
    if operation in milling_ops and operations.intersection(milling_ops):
        return True
    if operation in turning_ops and operations.intersection(turning_ops):
        return True
    return False


def _insert_operation_family_match(operation: str, applications: set[str], focus: set[str]) -> bool:
    turning_ops = {"turning", "production_turning", "general_turning", "interrupted_cut_candidate", "roughing"}
    milling_ops = {"milling", "general_milling", "dynamic_milling", "high_feed_milling"}
    if operation in turning_ops and (applications.intersection(turning_ops) or "turning" in focus):
        return True
    if operation in milling_ops and (applications.intersection(milling_ops) or "milling" in focus):
        return True
    return operation in focus


def _load_records(relative_path: Path, data_root: Path | None, label: str) -> list[dict]:
    root = data_root or DEFAULT_DATA_ROOT
    path = root / relative_path
    if not path.exists():
        return []
    records = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise ValueError(f"{label} data must be a list: {path}")
    return records


def _normalize(value: object) -> str:
    return str(value).strip().lower().replace(" ", "_").replace("-", "_")
