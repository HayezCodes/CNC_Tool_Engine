import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


REVIEWED_ROOT = REPO_ROOT / "tool_data" / "catalog_ingestion" / "reviewed"
COVERAGE_AUDIT_ROOT = REPO_ROOT / "tool_data" / "catalog_ingestion" / "coverage_audit"
REPORT_PATH = COVERAGE_AUDIT_ROOT / "catalog_family_coverage_report.json"

EXPECTED_BRANDS = [
    "Helical Solutions",
    "Harvey Tool",
    "Micro 100",
    "YG-1",
    "Garr Tool",
    "Niagara Cutter",
    "Sumitomo Electric",
    "Kyocera",
    "Tungaloy",
]

EXPECTED_SCOPE_SIGNALS = {
    "Helical Solutions": {
        "endmills": ["endmill"],
        "dynamic_adaptive": ["dynamic_milling", "adaptive_milling", "dynamic", "adaptive"],
        "aluminum": ["aluminum_milling", "aluminum_geometry"],
        "finishing": ["finishing", "surface_finish_priority"],
        "roughing": ["roughing", "chipbreaker_candidate"],
        "chamfer": ["chamfer", "chamfer_mill"],
    },
    "Harvey Tool": {
        "chamfer": ["chamfer", "chamfer_mill"],
        "keyseat": ["keyseat", "keyseat_cutter", "keyway"],
        "thread_mills": ["thread_mill", "thread_milling"],
        "miniature_endmills": ["miniature_endmill", "miniature_milling"],
        "undercut": ["undercut_tool", "undercutting"],
        "specialty": ["specialty_milling", "specialty_feature", "problem_solving"],
    },
    "Micro 100": {
        "boring_bars": ["boring_bar", "boring"],
        "miniature_turning": ["miniature_turning_tool", "small_feature_turning", "internal_turning"],
        "grooving": ["grooving_tool", "internal_grooving", "grooving"],
        "threading": ["threading_tool", "internal_threading", "threading"],
        "small_id_tooling": ["small_id_access", "small_id_candidate", "small_id_turning"],
    },
    "YG-1": {
        "endmills": ["endmill"],
        "drills": ["drill", "drilling"],
        "taps_threading": ["tap", "tapping", "threading"],
        "value_general_tooling": ["value_focused", "general_purpose", "job_shop_general"],
    },
    "Garr Tool": {
        "high_performance_endmills": ["endmill", "high_performance"],
        "roughing": ["roughing", "high_efficiency"],
        "finishing": ["finishing", "surface_finish_priority"],
        "aluminum_milling": ["aluminum_milling"],
        "ferrous_milling": ["P", "M", "S", "H"],
    },
    "Niagara Cutter": {
        "production_milling": ["production_milling"],
        "endmills": ["endmill"],
        "roughing": ["roughing"],
        "finishing": ["finishing"],
        "hss_cobalt_carbide_families": ["hss", "cobalt", "carbide", "solid_carbide"],
    },
    "Sumitomo Electric": {
        "turning_inserts": ["turning_insert", "external_turning", "internal_turning"],
        "milling_inserts": ["milling_insert", "face_milling", "shoulder_milling"],
        "drilling_indexable": ["drill", "indexable_drill", "drilling"],
        "production_insert_families": ["production_turning", "indexable_cutter", "insert_grade_verification_required"],
    },
    "Kyocera": {
        "turning_inserts": ["turning_insert", "external_turning", "internal_turning"],
        "milling_inserts": ["milling_insert", "face_milling", "shoulder_milling"],
        "drilling_indexable": ["drill", "indexable_drill", "drilling"],
        "production_insert_families": ["production_turning", "insert_grade_verification_required", "indexable_cutter"],
    },
    "Tungaloy": {
        "turning": ["turning", "production_turning", "turning_insert"],
        "grooving": ["grooving", "grooving_insert", "grooving_toolholder"],
        "threading": ["threading", "threading_insert", "threading_toolholder"],
        "high_feed_milling": ["high_feed_milling", "high_feed", "indexable_cutter"],
        "multifunction_indexable_tooling": ["multifunction", "multifunction_tooling", "tooling_system"],
    },
}

PROHIBITED_TERMS = {"sfm", "rpm", "feed", "feeds", "speeds", "chip_load", "diameter", "catalog_number"}


def build_catalog_family_coverage_report(reviewed_root: Path = REVIEWED_ROOT) -> dict[str, Any]:
    brand_reports: list[dict[str, Any]] = []
    for brand in EXPECTED_BRANDS:
        records, file_path = _load_brand_records(brand, reviewed_root)
        brand_reports.append(_build_brand_report(brand, records, file_path))

    return {
        "reviewed_root": str(reviewed_root),
        "total_reviewed_files": len(list(reviewed_root.glob("*.json"))) if reviewed_root.exists() else 0,
        "brands": brand_reports,
    }


def save_catalog_family_coverage_report(
    report: dict[str, Any],
    output_path: Path = REPORT_PATH,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output_path


def print_catalog_family_coverage_report(report: dict[str, Any]) -> None:
    print(f"Reviewed catalog root: {report['reviewed_root']}")
    print(f"Reviewed files scanned: {report['total_reviewed_files']}")
    print("")
    for brand_report in report["brands"]:
        print(f"{brand_report['brand']}")
        print(f"  reviewed file: {brand_report['reviewed_file_path']}")
        print(f"  total reviewed records: {brand_report['total_reviewed_records']}")
        print("  tool categories: " + _join(brand_report["tool_categories"]))
        print("  family names: " + _join(brand_report["family_names"]))
        print("  operation coverage: " + _join(brand_report["operation_fit_coverage"]))
        print("  material coverage: " + _join(brand_report["material_fit_coverage"]))
        print("  strategy coverage: " + _join(brand_report["strategy_fit_coverage"]))
        print("  geometry coverage: " + _join(brand_report["geometry_tags_coverage"]))
        print("  missing obvious categories: " + _join(brand_report["missing_obvious_family_categories"]))
        print("")


def main() -> None:
    report = build_catalog_family_coverage_report()
    output_path = save_catalog_family_coverage_report(report)
    print_catalog_family_coverage_report(report)
    print(f"Saved JSON report to {output_path}")


def _build_brand_report(brand: str, records: list[dict[str, Any]], file_path: Path | None) -> dict[str, Any]:
    tool_categories = sorted({record.get("tool_category", "") for record in records if record.get("tool_category")})
    family_names = sorted({record.get("family_name", "") for record in records if record.get("family_name")})
    operation_fit_coverage = sorted({item for record in records for item in _list_values(record.get("operation_fit", []))})
    material_fit_coverage = sorted({item for record in records for item in _list_values(record.get("material_fit", []))})
    strategy_fit_coverage = sorted({item for record in records for item in _list_values(record.get("strategy_fit", []))})
    geometry_tags_coverage = sorted({item for record in records for item in _list_values(record.get("geometry_tags", []))})
    missing_categories = _find_missing_categories(
        brand,
        tool_categories,
        family_names,
        operation_fit_coverage,
        material_fit_coverage,
        strategy_fit_coverage,
        geometry_tags_coverage,
    )

    return {
        "brand": brand,
        "reviewed_file_path": str(file_path) if file_path else "",
        "total_reviewed_records": len(records),
        "tool_categories": tool_categories,
        "family_names": family_names,
        "operation_fit_coverage": operation_fit_coverage,
        "material_fit_coverage": material_fit_coverage,
        "strategy_fit_coverage": strategy_fit_coverage,
        "geometry_tags_coverage": geometry_tags_coverage,
        "missing_obvious_family_categories": missing_categories,
    }


def _find_missing_categories(
    brand: str,
    tool_categories: list[str],
    family_names: list[str],
    operation_fit: list[str],
    material_fit: list[str],
    strategy_fit: list[str],
    geometry_tags: list[str],
) -> list[str]:
    searchable = {
        *_normalized_values(tool_categories),
        *_normalized_values(family_names),
        *_normalized_values(operation_fit),
        *_normalized_values(material_fit),
        *_normalized_values(strategy_fit),
        *_normalized_values(geometry_tags),
    }
    missing: list[str] = []
    for category_name, signals in EXPECTED_SCOPE_SIGNALS.get(brand, {}).items():
        normalized_signals = {_normalize(signal) for signal in signals}
        if not searchable.intersection(normalized_signals):
            missing.append(category_name)
    return missing


def _load_brand_records(brand: str, reviewed_root: Path) -> tuple[list[dict[str, Any]], Path | None]:
    if not reviewed_root.exists():
        return [], None

    normalized_brand = _normalize(brand)
    for path in sorted(reviewed_root.glob("*.json")):
        if path.name == ".gitkeep":
            continue
        records = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(records, list):
            continue
        brand_records = [record for record in records if _normalize(record.get("brand", "")) == normalized_brand]
        if brand_records:
            return brand_records, path
    return [], None


def _list_values(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    return []


def _normalized_values(values: list[str]) -> set[str]:
    return {_normalize(value) for value in values if _normalize(value)}


def _join(values: list[str]) -> str:
    return ", ".join(values) if values else "(none)"


def _normalize(value: object) -> str:
    return str(value).strip().lower().replace(" ", "_").replace("-", "_")


if __name__ == "__main__":
    main()
