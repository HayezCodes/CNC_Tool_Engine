import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from grade_engine.engine import resolve_grade_behavior
from grade_engine.resolver import map_behavior_to_supplier_grades


TOOL_DATA_ROOT = ROOT / "tool_data"
VALIDATION_ROOT = TOOL_DATA_ROOT / "validation"
REPORT_PATH = ROOT / "reports" / "grade_validation_report.txt"

STATUS_PASS = "PASS"
STATUS_FAIL = "FAIL"
STATUS_REVIEW = "REVIEW_NEEDED"

GENERAL_GRADE_TOKENS = {
    "",
    "generic",
    "various",
    "special",
    "coated",
    "gun_drill",
    "miracle",
}

BRAND_ALIASES = {
    "Sandvik Coromant": "Sandvik",
    "SANDVIK": "Sandvik",
    "Kyocera": "Kyocera",
    "KYOCERA": "Kyocera",
    "ISCAR": "ISCAR",
    "Mitsubishi Materials": "Mitsubishi",
    "Mitsubishi": "Mitsubishi",
    "Allied Machine & Engineering": "Allied",
    "Allied": "Allied",
    "WIDIA": "WIDIA",
}

DATASET_SPECS = [
    {"name": "grade_map_baseline", "path": "grade_maps/grades.json"},
    {"name": "turning_inserts", "path": "normalized/turning/inserts.json"},
    {"name": "threading_inserts", "path": "normalized/threading/inserts.json"},
    {"name": "grooving_inserts", "path": "normalized/grooving/inserts.json"},
    {"name": "solid_drills", "path": "normalized/drilling/solid_drills.json"},
    {"name": "indexable_drills", "path": "normalized/drilling/indexable_drills.json"},
    {"name": "endmills", "path": "normalized/milling/endmills.json"},
    {"name": "indexable_cutters", "path": "normalized/milling/indexable_cutters.json"},
]

SCENARIO_DATASET_PATHS = {
    "drilling": [
        TOOL_DATA_ROOT / "normalized/drilling/solid_drills.json",
        TOOL_DATA_ROOT / "normalized/drilling/indexable_drills.json",
    ],
    "milling": [
        TOOL_DATA_ROOT / "normalized/milling/endmills.json",
        TOOL_DATA_ROOT / "normalized/milling/indexable_cutters.json",
    ],
    "grooving": [TOOL_DATA_ROOT / "normalized/grooving/inserts.json"],
    "threading": [TOOL_DATA_ROOT / "normalized/threading/inserts.json"],
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_company(company: str) -> str:
    return BRAND_ALIASES.get(company, company)


def normalize_iso_groups(record: dict[str, Any]) -> list[str]:
    if "primary_iso_group" in record and record["primary_iso_group"]:
        return [record["primary_iso_group"]]
    materials = record.get("materials", {})
    if isinstance(materials, dict):
        values = materials.get("iso_groups") or materials.get("preferred_groups") or []
        if isinstance(values, str):
            return [values]
        if isinstance(values, list):
            return [str(value) for value in values if value]
    return []


def zone_to_cut_style(zone: str) -> str:
    return {"WEAR": "finish", "BALANCED": "medium", "TOUGH": "rough"}.get(zone, "general")


def classify_turning_cut_style(record: dict[str, Any]) -> str:
    cut_styles = record.get("application", {}).get("cut_style", [])
    if isinstance(cut_styles, str):
        cut_styles = [cut_styles]
    for style in cut_styles:
        lowered = style.lower()
        if "finish" in lowered or "wiper" in lowered:
            return "finish"
        if "rough" in lowered or "heavy" in lowered:
            return "rough"
        if "medium" in lowered or "general" in lowered:
            return "medium"
    if record.get("engine_zone"):
        return zone_to_cut_style(record["engine_zone"])
    return "medium"


def classify_drilling_cut_style(record: dict[str, Any]) -> str:
    subcategory = str(record.get("subcategory", "")).lower()
    series = str(record.get("series", "")).lower()
    if "reference" in subcategory or record.get("geometry", {}).get("coolant") == "reference":
        return "reference"
    if record.get("tool_category") == "indexable_drill":
        return "productivity"
    available_l_d = record.get("geometry", {}).get("available_l_d", [])
    if isinstance(available_l_d, list) and available_l_d:
        if max(available_l_d) >= 8:
            return "deep_hole"
    if "super long" in series or "gun" in subcategory:
        return "deep_hole"
    return "general"


def classify_grooving_cut_style(record: dict[str, Any]) -> str:
    operations = record.get("application", {}).get("operations", [])
    if any(op in operations for op in ["cutoff", "parting"]):
        return "rough"
    if any(op in operations for op in ["face_grooving", "undercutting", "id_grooving"]):
        return "finish"
    return "general"


def classify_threading_cut_style(record: dict[str, Any]) -> str:
    return "general"


def classify_milling_cut_style(record: dict[str, Any]) -> str:
    application = record.get("application", {})
    strategy = str(application.get("strategy", "")).lower()
    operations = application.get("operations", [])
    if any(token in strategy for token in ["finish", "high_velocity", "semi_finish"]):
        return "finish"
    if any(token in strategy for token in ["rough", "trochoidal"]):
        return "rough"
    if any(op in operations for op in ["high_feed_milling", "plunge_milling", "plunging"]):
        return "rough"
    return "medium"


def classify_operation_family(spec_name: str) -> str:
    if spec_name == "grade_map_baseline":
        return "turning"
    if "turning" in spec_name:
        return "turning"
    if "threading" in spec_name:
        return "threading"
    if "grooving" in spec_name:
        return "grooving"
    if "drill" in spec_name:
        return "drilling"
    if spec_name in {"endmills", "indexable_cutters"}:
        return "milling"
    return "unknown"


def classify_cut_style(spec_name: str, record: dict[str, Any]) -> str:
    if spec_name == "grade_map_baseline":
        return zone_to_cut_style(record.get("zone", "BALANCED"))
    if spec_name == "turning_inserts":
        return classify_turning_cut_style(record)
    if spec_name == "threading_inserts":
        return classify_threading_cut_style(record)
    if spec_name == "grooving_inserts":
        return classify_grooving_cut_style(record)
    if spec_name in {"solid_drills", "indexable_drills"}:
        return classify_drilling_cut_style(record)
    if spec_name in {"endmills", "indexable_cutters"}:
        return classify_milling_cut_style(record)
    return "general"


def extract_grades(record: dict[str, Any]) -> list[str]:
    grades: list[str] = []
    if record.get("grade"):
        grades.append(str(record["grade"]))
    if record.get("grade_or_coating"):
        grades.append(str(record["grade_or_coating"]))
    insert_grade = record.get("insert_system", {}).get("grade")
    if insert_grade:
        grades.append(str(insert_grade))
    for grade in record.get("recommended_grades", []):
        grades.append(str(grade))
    deduped: list[str] = []
    seen = set()
    for grade in grades:
        if grade not in seen:
            deduped.append(grade)
            seen.add(grade)
    return deduped


def is_generic_grade(grade: str) -> bool:
    return grade.strip().lower() in GENERAL_GRADE_TOKENS


def find_coverage_gaps(
    rules: dict[str, Any],
    company: str,
    iso_groups: list[str],
    operation_family: str,
    cut_style: str,
) -> list[tuple[str, str, str]]:
    coverage_gaps: list[tuple[str, str, str]] = []
    company_rules = rules.get(company)
    if not company_rules:
        return [(company, iso_group, operation_family) for iso_group in (iso_groups or ["<unknown>"])]

    for iso_group in iso_groups or ["<unknown>"]:
        iso_rules = company_rules.get(iso_group)
        if not iso_rules:
            coverage_gaps.append((company, iso_group, operation_family))
            continue
        op_rules = iso_rules.get(operation_family)
        if not op_rules:
            coverage_gaps.append((company, iso_group, operation_family))
            continue
        if cut_style not in op_rules and "general" not in op_rules:
            coverage_gaps.append((company, iso_group, operation_family))
    return coverage_gaps


def validate_grade_against_rules(
    rules: dict[str, Any],
    company: str,
    iso_groups: list[str],
    operation_family: str,
    cut_style: str,
    grade: str,
) -> tuple[str, str, list[tuple[str, str, str]]]:
    coverage_gaps = find_coverage_gaps(rules, company, iso_groups, operation_family, cut_style)
    if not grade:
        return STATUS_REVIEW, "No grade on record.", coverage_gaps
    if is_generic_grade(grade):
        return STATUS_REVIEW, f"Grade '{grade}' is a placeholder or generic coating token and needs manual review.", coverage_gaps

    company_rules = rules.get(company)
    if not company_rules:
        return STATUS_REVIEW, f"No approved-rule entry for company '{company}'.", coverage_gaps

    found_specific_bucket = False
    found_general_bucket = False
    fallback_match = False
    allowed_examples: list[str] = []

    for iso_group in iso_groups or ["<unknown>"]:
        iso_rules = company_rules.get(iso_group)
        if not iso_rules:
            continue
        op_rules = iso_rules.get(operation_family)
        if not op_rules:
            continue
        if cut_style in op_rules:
            found_specific_bucket = True
            allowed = [str(item) for item in op_rules.get(cut_style, [])]
            allowed_examples.extend(allowed)
            if grade in allowed:
                return STATUS_PASS, f"{grade} matched {company}/{iso_group}/{operation_family}/{cut_style}.", coverage_gaps
        elif "general" in op_rules:
            found_general_bucket = True
            allowed = [str(item) for item in op_rules.get("general", [])]
            allowed_examples.extend(allowed)
            if grade in allowed:
                fallback_match = True

    if fallback_match:
        return STATUS_REVIEW, f"{grade} matched only the general bucket for {company}/{operation_family}; style-specific coverage is incomplete.", coverage_gaps

    unique_examples = sorted({item for item in allowed_examples if item})
    if found_specific_bucket or found_general_bucket:
        example_text = ", ".join(unique_examples[:6]) if unique_examples else "no approved grades listed"
        return STATUS_FAIL, f"{grade} is not in the approved grades for {company}/{operation_family}/{cut_style}. Allowed examples: {example_text}.", coverage_gaps

    return STATUS_REVIEW, f"No approved rule bucket for {company}/{operation_family}/{cut_style}.", coverage_gaps


def build_dataset_context(spec_name: str, record: dict[str, Any]) -> dict[str, Any]:
    company = normalize_company(record.get("brand", "Unknown"))
    return {
        "record_id": record.get("id", "<no-id>"),
        "brand": company,
        "raw_brand": record.get("brand", company),
        "series": record.get("series", ""),
        "iso_groups": normalize_iso_groups(record),
        "operation_family": classify_operation_family(spec_name),
        "cut_style": classify_cut_style(spec_name, record),
        "grades": extract_grades(record),
    }


def validate_datasets(rules: dict[str, Any]) -> tuple[list[dict[str, Any]], set[tuple[str, str, str]], list[str]]:
    results: list[dict[str, Any]] = []
    missing_coverage: set[tuple[str, str, str]] = set()
    limitations: list[str] = []

    for spec in DATASET_SPECS:
        rows = load_json(TOOL_DATA_ROOT / spec["path"])
        spec_name = spec["name"]
        for record in rows:
            context = build_dataset_context(spec_name, record)
            if not context["grades"]:
                results.append(
                    {
                        "dataset": spec_name,
                        "record_id": context["record_id"],
                        "brand": context["brand"],
                        "iso_groups": context["iso_groups"],
                        "operation_family": context["operation_family"],
                        "cut_style": context["cut_style"],
                        "grade": "",
                        "status": STATUS_REVIEW,
                        "message": "No grade field on this record; family-level data only.",
                    }
                )
                if context["operation_family"] == "milling":
                    limitations.append(f"{spec_name} carries family/application data but no explicit grades on record {context['record_id']}.")
                continue

            for grade in context["grades"]:
                status, message, coverage_gaps = validate_grade_against_rules(
                    rules,
                    context["brand"],
                    context["iso_groups"],
                    context["operation_family"],
                    context["cut_style"],
                    grade,
                )
                missing_coverage.update(coverage_gaps)
                results.append(
                    {
                        "dataset": spec_name,
                        "record_id": context["record_id"],
                        "brand": context["brand"],
                        "iso_groups": context["iso_groups"],
                        "operation_family": context["operation_family"],
                        "cut_style": context["cut_style"],
                        "grade": grade,
                        "status": status,
                        "message": message,
                    }
                )

    return results, missing_coverage, sorted(set(limitations))


def expected_zone_allowed(scenario: dict[str, Any]) -> bool:
    cut_style = scenario.get("cut_style", "general")
    zone = scenario.get("expected_grade_zone", "BALANCED")
    allowed = {
        "finish": {"WEAR", "BALANCED"},
        "medium": {"BALANCED"},
        "rough": {"TOUGH", "BALANCED"},
        "general": {"BALANCED", "TOUGH"},
        "productivity": {"TOUGH", "BALANCED"},
        "deep_hole": {"BALANCED"},
        "reference": {"BALANCED"},
    }.get(cut_style, {"BALANCED"})
    if scenario.get("interruption") == "HEAVY" or scenario.get("stability") == "POOR":
        allowed = {candidate for candidate in allowed if candidate != "WEAR"} or allowed
    return zone in allowed


def scenario_to_common_inputs(scenario: dict[str, Any]) -> dict[str, Any]:
    return {
        "material_group": scenario["iso_group"],
        "application_zone": scenario.get("application_zone", scenario["expected_grade_zone"]),
        "interrupted_cut": scenario.get("interruption", "NONE"),
        "stickout": scenario.get("stickout", "NORMAL"),
        "workholding": scenario.get("stability", "GOOD"),
        "cutting_speed_band": scenario.get("speed_level", "NORMAL"),
        "doc_band": scenario.get("doc_level", "MEDIUM"),
        "finish_priority": scenario.get("finish_priority", "NORMAL"),
    }


def normalize_supplier_results(results: dict[str, Any]) -> dict[str, Any]:
    normalized = {}
    for company, payload in results.items():
        normalized[normalize_company(company)] = payload
    return normalized


def run_turning_scenario(rules: dict[str, Any], scenario: dict[str, Any]) -> tuple[str, str, list[tuple[str, str, str]]]:
    common = scenario_to_common_inputs(scenario)
    behavior = resolve_grade_behavior(common)
    supplier_results = normalize_supplier_results(
        map_behavior_to_supplier_grades(
            behavior["material_group"],
            behavior["application_zone"],
            behavior["preferred_coating"],
            behavior["geometry_hint"],
            behavior["chipbreaker_hint"],
            behavior["insert_identity"],
        )
    )

    if not supplier_results:
        return STATUS_FAIL, "Turning scenario returned no supplier-grade suggestions.", []

    coverage_gaps: list[tuple[str, str, str]] = []
    expected_companies = scenario.get("expected_companies") or sorted(supplier_results.keys())
    company_messages: list[str] = []
    statuses: list[str] = []

    for company in expected_companies:
        payload = supplier_results.get(company)
        if not payload:
            statuses.append(STATUS_FAIL)
            company_messages.append(f"{company}: missing from supplier output")
            continue
        grade = payload.get("recommended_grade", "")
        status, message, gaps = validate_grade_against_rules(
            rules,
            company,
            [scenario["iso_group"]],
            "turning",
            scenario["cut_style"],
            grade,
        )
        coverage_gaps.extend(gaps)
        statuses.append(status)
        company_messages.append(f"{company}: {grade} -> {status}")

    if not expected_zone_allowed(scenario):
        statuses.append(STATUS_FAIL)
        company_messages.append("Expected grade zone is not reasonable for the requested cut style and stability inputs.")

    if behavior["application_zone"] != scenario["expected_grade_zone"]:
        statuses.append(STATUS_FAIL)
        company_messages.append(
            f"Scenario expected zone {scenario['expected_grade_zone']}, but the common inputs drove {behavior['application_zone']}."
        )

    if STATUS_FAIL in statuses:
        overall = STATUS_FAIL
    elif STATUS_REVIEW in statuses:
        overall = STATUS_REVIEW
    else:
        overall = STATUS_PASS

    detail = (
        f"Resolved {behavior['recommendation_title']} with coating bias {behavior['preferred_coating']}. "
        + " | ".join(company_messages)
    )
    return overall, detail, coverage_gaps


def match_scenario_records(scenario: dict[str, Any], rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    matched: list[dict[str, Any]] = []
    iso_group = scenario["iso_group"]
    expected_companies = {normalize_company(company) for company in scenario.get("expected_companies", [])}
    operation_detail = scenario.get("operation_detail", "")

    for record in rows:
        brand = normalize_company(record.get("brand", "Unknown"))
        if expected_companies and brand not in expected_companies:
            continue

        iso_groups = normalize_iso_groups(record)
        if iso_groups and iso_group not in iso_groups:
            continue

        operations = record.get("application", {}).get("operations", [])
        strategy = str(record.get("application", {}).get("strategy", ""))
        if scenario["module"] == "threading" and operation_detail and operation_detail not in operations:
            continue
        if scenario["module"] == "grooving" and operation_detail and operation_detail not in operations:
            continue
        if scenario["module"] == "milling":
            if operation_detail and operation_detail not in operations and operation_detail != strategy:
                continue
        if scenario["module"] == "drilling":
            detail = operation_detail.lower()
            if detail == "solid_carbide" and record.get("tool_category") != "solid_drill":
                continue
            if detail == "indexable" and record.get("tool_category") != "indexable_drill":
                continue

        matched.append(record)

    return matched


def run_dataset_backed_scenario(rules: dict[str, Any], scenario: dict[str, Any]) -> tuple[str, str, list[tuple[str, str, str]]]:
    coverage_gaps: list[tuple[str, str, str]] = []
    rows: list[dict[str, Any]] = []
    for path in SCENARIO_DATASET_PATHS.get(scenario["module"], []):
        rows.extend(load_json(path))

    matched = match_scenario_records(scenario, rows)
    if not matched:
        return STATUS_FAIL, "No dataset records matched the scenario filters.", coverage_gaps

    validated_any = False
    statuses: list[str] = []
    details: list[str] = []

    for record in matched:
        brand = normalize_company(record.get("brand", "Unknown"))
        grades = extract_grades(record)
        if not grades:
            statuses.append(STATUS_REVIEW)
            details.append(f"{brand} {record.get('series', '')}: no grade on record")
            continue
        cut_style = classify_drilling_cut_style(record) if scenario["module"] == "drilling" else scenario["cut_style"]
        for grade in grades:
            status, message, gaps = validate_grade_against_rules(
                rules,
                brand,
                normalize_iso_groups(record) or [scenario["iso_group"]],
                scenario["operation_family"],
                cut_style,
                grade,
            )
            validated_any = True
            coverage_gaps.extend(gaps)
            statuses.append(status)
            details.append(f"{brand} {record.get('series', '')}: {grade} -> {status}")

    if not expected_zone_allowed(scenario):
        statuses.append(STATUS_FAIL)
        details.append("Scenario grade zone is not reasonable for the requested cut style and setup.")

    if scenario["module"] != "turning":
        details.append("Scenario uses dataset-backed validation only; there is no pure non-UI recommendation function for this module yet.")

    if not validated_any:
        statuses.append(STATUS_REVIEW)
        details.append("Matched records did not expose precise grades, so this remains manual-review territory.")

    if STATUS_FAIL in statuses:
        overall = STATUS_FAIL
    elif STATUS_REVIEW in statuses:
        overall = STATUS_REVIEW
    else:
        overall = STATUS_PASS

    return overall, " | ".join(details[:8]), coverage_gaps


def validate_scenarios(rules: dict[str, Any], scenarios: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], set[tuple[str, str, str]], list[str]]:
    results: list[dict[str, Any]] = []
    missing_coverage: set[tuple[str, str, str]] = set()
    limitations: list[str] = []

    for scenario in scenarios:
        if scenario["module"] == "turning":
            status, message, gaps = run_turning_scenario(rules, scenario)
        else:
            status, message, gaps = run_dataset_backed_scenario(rules, scenario)
            limitations.append(
                f"Scenario {scenario['id']} used dataset-backed validation because {scenario['module']} does not expose a reusable non-UI recommendation function yet."
            )
        missing_coverage.update(gaps)
        results.append(
            {
                "scenario_id": scenario["id"],
                "module": scenario["module"],
                "iso_group": scenario["iso_group"],
                "cut_style": scenario["cut_style"],
                "status": status,
                "message": message,
            }
        )

    return results, missing_coverage, sorted(set(limitations))


def summarize_statuses(results: list[dict[str, Any]]) -> Counter:
    return Counter(result["status"] for result in results)


def build_report(
    dataset_results: list[dict[str, Any]],
    scenario_results: list[dict[str, Any]],
    dataset_missing: set[tuple[str, str, str]],
    scenario_missing: set[tuple[str, str, str]],
    dataset_limitations: list[str],
    scenario_limitations: list[str],
) -> str:
    dataset_counts = summarize_statuses(dataset_results)
    scenario_counts = summarize_statuses(scenario_results)
    failures = [result for result in dataset_results + scenario_results if result["status"] == STATUS_FAIL]
    review_needed = [result for result in dataset_results + scenario_results if result["status"] == STATUS_REVIEW]
    missing = sorted(dataset_missing | scenario_missing)

    lines: list[str] = []
    lines.append("1. SUMMARY")
    lines.append(
        f"- Dataset checks: {len(dataset_results)} items -> PASS {dataset_counts[STATUS_PASS]}, FAIL {dataset_counts[STATUS_FAIL]}, REVIEW_NEEDED {dataset_counts[STATUS_REVIEW]}"
    )
    lines.append(
        f"- Scenario checks: {len(scenario_results)} items -> PASS {scenario_counts[STATUS_PASS]}, FAIL {scenario_counts[STATUS_FAIL]}, REVIEW_NEEDED {scenario_counts[STATUS_REVIEW]}"
    )
    lines.append("- The validator compares current project datasets and scenario outputs against approved brand/ISO/operation/cut-style grade rules.")
    lines.append("")

    lines.append("2. DATASET VALIDATION RESULTS")
    for result in dataset_results[:40]:
        lines.append(
            f"- [{result['status']}] {result['dataset']} :: {result['brand']} :: {result['record_id']} :: "
            f"{'/'.join(result['iso_groups']) or '<no-iso>'} :: {result['operation_family']} :: {result['cut_style']} :: "
            f"{result['grade'] or '<no-grade>'} :: {result['message']}"
        )
    if len(dataset_results) > 40:
        lines.append(f"- ... {len(dataset_results) - 40} more dataset validation rows omitted from the text report for brevity.")
    lines.append("")

    lines.append("3. SCENARIO VALIDATION RESULTS")
    for result in scenario_results:
        lines.append(
            f"- [{result['status']}] {result['scenario_id']} :: {result['module']} :: {result['iso_group']} :: {result['cut_style']} :: {result['message']}"
        )
    lines.append("")

    lines.append("4. FAILURES")
    if failures:
        for result in failures:
            identifier = result.get("record_id", result.get("scenario_id", "<unknown>"))
            lines.append(f"- {identifier}: {result['message']}")
    else:
        lines.append("- None.")
    lines.append("")

    lines.append("5. REVIEW_NEEDED")
    if review_needed:
        for result in review_needed[:40]:
            identifier = result.get("record_id", result.get("scenario_id", "<unknown>"))
            lines.append(f"- {identifier}: {result['message']}")
        if len(review_needed) > 40:
            lines.append(f"- ... {len(review_needed) - 40} more review-needed rows omitted from the text report for brevity.")
    else:
        lines.append("- None.")
    lines.append("")

    lines.append("6. MISSING RULE COVERAGE")
    if missing:
        for company, iso_group, operation_family in missing:
            lines.append(f"- {company} / {iso_group} / {operation_family}")
    else:
        lines.append("- None.")
    lines.append("")

    lines.append("7. LIMITATIONS")
    all_limitations = sorted(set(dataset_limitations + scenario_limitations))
    if all_limitations:
        for limitation in all_limitations:
            lines.append(f"- {limitation}")
    else:
        lines.append("- None.")
    lines.append("")

    lines.append("8. NEXT CLEANUP ACTIONS")
    lines.append("- Reconcile supplier-map grades that do not exist in the approved dataset-backed rule set.")
    lines.append("- Replace generic drill coatings/placeholders with brand-and-ISO-specific drill grade entries where the source catalogs support it.")
    lines.append("- Add explicit grade fields to milling and grooving records if those modules need true grade-level proofing.")
    lines.append("- Split broad grade-map category assignments where a grade is valid for turning but not proven for threading or grooving.")
    lines.append("- Expand WIDIA and Allied coverage only after the underlying dataset carries precise grades instead of generic placeholders.")
    return "\n".join(lines) + "\n"


def print_console_summary(dataset_results: list[dict[str, Any]], scenario_results: list[dict[str, Any]]) -> None:
    dataset_counts = summarize_statuses(dataset_results)
    scenario_counts = summarize_statuses(scenario_results)
    print("GRADE VALIDATION SUMMARY")
    print(
        f"Dataset checks: {len(dataset_results)} total | PASS {dataset_counts[STATUS_PASS]} | "
        f"FAIL {dataset_counts[STATUS_FAIL]} | REVIEW_NEEDED {dataset_counts[STATUS_REVIEW]}"
    )
    print(
        f"Scenario checks: {len(scenario_results)} total | PASS {scenario_counts[STATUS_PASS]} | "
        f"FAIL {scenario_counts[STATUS_FAIL]} | REVIEW_NEEDED {scenario_counts[STATUS_REVIEW]}"
    )

    top_failures = [result for result in dataset_results + scenario_results if result["status"] == STATUS_FAIL][:10]
    if top_failures:
        print("\nTop FAIL items:")
        for result in top_failures:
            identifier = result.get("record_id", result.get("scenario_id", "<unknown>"))
            print(f"- {identifier}: {result['message']}")

    top_reviews = [result for result in dataset_results + scenario_results if result["status"] == STATUS_REVIEW][:10]
    if top_reviews:
        print("\nTop REVIEW_NEEDED items:")
        for result in top_reviews:
            identifier = result.get("record_id", result.get("scenario_id", "<unknown>"))
            print(f"- {identifier}: {result['message']}")

    print(f"\nReport written to: {REPORT_PATH}")


def main() -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    VALIDATION_ROOT.mkdir(parents=True, exist_ok=True)

    rules = load_json(VALIDATION_ROOT / "approved_grade_rules.json")
    scenarios = load_json(VALIDATION_ROOT / "test_scenarios.json")["scenarios"]

    dataset_results, dataset_missing, dataset_limitations = validate_datasets(rules)
    scenario_results, scenario_missing, scenario_limitations = validate_scenarios(rules, scenarios)

    report = build_report(
        dataset_results,
        scenario_results,
        dataset_missing,
        scenario_missing,
        dataset_limitations,
        scenario_limitations,
    )
    REPORT_PATH.write_text(report, encoding="utf-8")
    print_console_summary(dataset_results, scenario_results)


if __name__ == "__main__":
    main()
