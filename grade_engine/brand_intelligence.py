import json
from pathlib import Path
from typing import Any


DEFAULT_DATA_ROOT = Path(__file__).resolve().parent.parent / "tool_data"
BRAND_DATA_PATH = Path("brand_intelligence") / "tool_brands.json"

PRIORITY_TERMS = {
    "balanced": [],
    "value": ["value", "budget", "value alternative", "cost effective", "easy sourcing", "job shop"],
    "high_performance": ["high_performance", "high performance", "dynamic milling", "production milling"],
    "specialty": ["specialty", "miniature", "problem solving", "keyseat", "chamfer", "undercutting"],
    "production_turning": ["production_turning", "production turning", "turning_inserts", "indexable"],
    "small_bore": ["small_bore", "small bore", "miniature", "boring_bars", "small_id_work"],
}


def load_brand_intelligence(data_root: Path | None = None) -> list[dict]:
    root = data_root or DEFAULT_DATA_ROOT
    path = root / BRAND_DATA_PATH
    if not path.exists():
        return []
    records = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        raise ValueError(f"Brand intelligence data must be a list: {path}")
    return records


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


def _operation_family_match(operation: str, operations: set[str]) -> bool:
    milling_ops = {"general_milling", "dynamic_milling", "aluminum_milling", "keyseat", "chamfer"}
    turning_ops = {"turning", "production_turning", "grooving", "small_bore"}
    if operation in milling_ops and operations.intersection(milling_ops):
        return True
    if operation in turning_ops and operations.intersection(turning_ops):
        return True
    return False


def _normalize(value: object) -> str:
    return str(value).strip().lower().replace(" ", "_").replace("-", "_")
