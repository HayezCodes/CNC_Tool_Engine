from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any

from .index import load_lookup_records
from .normalize import normalize_tool_number, parse_tool_number_tokens


def _safe_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value if item not in (None, "")]
    return [str(value)]


def _string_fields(record: dict[str, Any]) -> list[str]:
    return [
        str(record.get("manufacturer_number", "")),
        str(record.get("manufacturer_reference", "")),
        str(record.get("designation", "")),
        str(record.get("series", "")),
        str(record.get("brand", "")),
    ]


def _designation_prefixes(value: str) -> list[str]:
    normalized = normalize_tool_number(value)
    if not normalized:
        return []
    prefixes: list[str] = []
    parsed = parse_tool_number_tokens(normalized)
    if parsed["designation_prefix"]:
        prefixes.append(parsed["designation_prefix"])
    if normalized.startswith("COROMILL"):
        prefixes.extend(["COROMILL", normalized])
    if normalized.startswith("CORODRILL"):
        prefixes.extend(["CORODRILL", normalized])

    letter_prefix = ""
    for char in normalized:
        if char.isalpha():
            letter_prefix += char
        else:
            break
    if len(letter_prefix) >= 2:
        prefixes.append(letter_prefix)
        prefixes.append(letter_prefix[:2])

    digit_prefix = ""
    started_digit = False
    for char in normalized:
        if char.isdigit() and not started_digit:
            digit_prefix += char
        elif char.isalpha():
            digit_prefix += char
            started_digit = True
        else:
            if started_digit:
                break
    if len(digit_prefix) >= 4:
        prefixes.append(digit_prefix)
    return list(dict.fromkeys(prefixes))


def _record_tokens(record: dict[str, Any]) -> dict[str, str]:
    base_value = (
        str(record.get("manufacturer_number", "")).strip()
        or str(record.get("manufacturer_reference", "")).strip()
        or str(record.get("designation", "")).strip()
        or str(record.get("series", "")).strip()
    )
    tokens = parse_tool_number_tokens(base_value)
    if not tokens["designation_prefix"]:
        designation = str(record.get("designation", "")).strip()
        if designation:
            tokens["designation_prefix"] = parse_tool_number_tokens(designation)["designation_prefix"]
    if not tokens["suffix_token"]:
        chipbreaker = str(record.get("geometry", {}).get("chipbreaker", "")).strip().upper()
        if chipbreaker:
            tokens["suffix_token"] = chipbreaker
    if not tokens["grade_token"]:
        grade = str(record.get("grade", "")).strip().upper()
        if grade:
            tokens["grade_token"] = normalize_tool_number(grade)
    return tokens


def _strong_partial_exact_style_match(
    query_tokens: dict[str, str],
    record_tokens: dict[str, str],
    record: dict[str, Any],
) -> tuple[float, list[str]]:
    score = 0.0
    reasons: list[str] = []

    if not query_tokens["designation_prefix"] or not record_tokens["designation_prefix"]:
        return score, reasons
    if query_tokens["designation_prefix"] != record_tokens["designation_prefix"]:
        return score, reasons

    score += 6.0
    reasons.append("same designation prefix")

    if query_tokens["size_token"] and record_tokens["size_token"]:
        if query_tokens["size_token"] == record_tokens["size_token"]:
            score += 6.0
            reasons.append("same ANSI size chunk")
        else:
            return 0.0, []

    if query_tokens["suffix_token"] and record_tokens["suffix_token"]:
        if query_tokens["suffix_token"] == record_tokens["suffix_token"]:
            score += 5.0
            reasons.append("same chipbreaker / suffix")
        else:
            return 0.0, []

    if query_tokens["grade_token"] and record_tokens["grade_token"]:
        if query_tokens["grade_token"] == record_tokens["grade_token"]:
            score += 4.0
            reasons.append("same grade chunk")
        else:
            return 0.0, []

    if record.get("tool_category") == "turning_insert":
        score += 3.0
        reasons.append("turning insert family")
    elif record.get("tool_category") == "threading_insert":
        score += 2.0
        reasons.append("threading family")

    if query_tokens["designation_prefix"] and query_tokens["suffix_token"]:
        reasons.append("strong insert-style match")

    return score, reasons


def _match_seed(record: dict[str, Any], normalized_query: str) -> bool:
    if not normalized_query:
        return False
    for field in _string_fields(record):
        normalized_field = normalize_tool_number(field)
        if normalized_field and (
            normalized_query in normalized_field or normalized_field in normalized_query
        ):
            return True
    return False


def _seed_profile(records: list[dict[str, Any]], normalized_query: str) -> dict[str, set[str]]:
    seeds = [record for record in records if _match_seed(record, normalized_query)]
    iso_groups: set[str] = set()
    operations: set[str] = set()
    chipbreakers: set[str] = set()
    tool_categories: set[str] = set()
    for record in seeds:
        iso_groups.update(_safe_list(record.get("materials", {}).get("iso_groups", [])))
        operations.update(_safe_list(record.get("application", {}).get("operations", [])))
        if record.get("tool_category"):
            tool_categories.add(str(record["tool_category"]))
        chipbreaker = record.get("geometry", {}).get("chipbreaker")
        if isinstance(chipbreaker, str) and chipbreaker.strip():
            chipbreakers.add(chipbreaker.strip().upper())
    return {
        "iso_groups": iso_groups,
        "operations": operations,
        "chipbreakers": chipbreakers,
        "tool_categories": tool_categories,
    }


def _exact_match(records: list[dict[str, Any]], normalized_query: str) -> dict[str, Any] | None:
    if not normalized_query:
        return None
    for record in records:
        if normalized_query and record.get("normalized_number") == normalized_query:
            return record
    for record in records:
        for field in ("manufacturer_reference", "designation", "series"):
            if normalize_tool_number(record.get(field, "")) == normalized_query:
                return record
    return None


def _score_record(
    record: dict[str, Any],
    normalized_query: str,
    query_tokens: dict[str, str],
    query_prefixes: list[str],
    seed_profile: dict[str, set[str]],
    tool_category: str | None,
    brand: str | None,
) -> tuple[float, list[str]]:
    score = 0.0
    reasons: list[str] = []
    normalized_fields = {
        "manufacturer_reference": normalize_tool_number(record.get("manufacturer_reference", "")),
        "designation": normalize_tool_number(record.get("designation", "")),
        "series": normalize_tool_number(record.get("series", "")),
        "manufacturer_number": normalize_tool_number(record.get("manufacturer_number", "")),
    }
    record_tokens = _record_tokens(record)

    if tool_category and record.get("tool_category") == tool_category:
        score += 2.0
        reasons.append("same tool category")
    if brand and record.get("brand") == brand:
        score += 2.0
        reasons.append("same brand")
    if seed_profile["tool_categories"]:
        if record.get("tool_category") in seed_profile["tool_categories"]:
            score += 2.0
            reasons.append("same seed tool category")
        else:
            score -= 3.0

    if normalized_query:
        for label, normalized_field in normalized_fields.items():
            if not normalized_field:
                continue
            if normalized_query == normalized_field:
                score += 10.0
                reasons.append(f"exact {label} match")
            elif normalized_query in normalized_field:
                score += 5.0
                reasons.append(f"{label} contains query")
            elif normalized_field in normalized_query:
                score += 4.0
                reasons.append(f"query expands {label}")

            similarity = SequenceMatcher(None, normalized_query, normalized_field).ratio()
            if similarity >= 0.6:
                score += round(similarity * 3.0, 2)
                reasons.append(f"similar {label}")

    partial_score, partial_reasons = _strong_partial_exact_style_match(query_tokens, record_tokens, record)
    if partial_score:
        score += partial_score
        reasons.extend(partial_reasons)

    record_prefixes = []
    for field in (
        record.get("manufacturer_reference", ""),
        record.get("designation", ""),
        record.get("series", ""),
    ):
        record_prefixes.extend(_designation_prefixes(str(field)))
    record_prefixes = list(dict.fromkeys(record_prefixes))

    if any(prefix and prefix in record_prefixes for prefix in query_prefixes):
        score += 4.0
        reasons.append("same designation prefix")
    elif any(
        query_prefix and record_prefix and (
            query_prefix.startswith(record_prefix) or record_prefix.startswith(query_prefix)
        )
        for query_prefix in query_prefixes
        for record_prefix in record_prefixes
    ):
        score += 2.5
        reasons.append("related designation prefix")

    record_groups = set(_safe_list(record.get("materials", {}).get("iso_groups", [])))
    shared_groups = sorted(record_groups & seed_profile["iso_groups"])
    if shared_groups:
        score += min(3.0, float(len(shared_groups)))
        reasons.append("shared ISO groups: " + ", ".join(shared_groups))

    record_operations = set(_safe_list(record.get("application", {}).get("operations", [])))
    shared_operations = sorted(record_operations & seed_profile["operations"])
    if shared_operations:
        score += min(3.0, float(len(shared_operations)))
        reasons.append("shared operations: " + ", ".join(shared_operations[:3]))

    chipbreaker = record.get("geometry", {}).get("chipbreaker")
    if isinstance(chipbreaker, str) and chipbreaker.strip():
        if chipbreaker.strip().upper() in seed_profile["chipbreakers"]:
            score += 1.5
            reasons.append("similar chipbreaker")

    if query_tokens["designation_prefix"] and record_tokens["designation_prefix"]:
        if query_tokens["designation_prefix"] == record_tokens["designation_prefix"]:
            score += 2.0
            reasons.append("same normalized designation")
    if query_tokens["grade_token"] and record_tokens["grade_token"]:
        if query_tokens["grade_token"] == record_tokens["grade_token"]:
            score += 2.0
            reasons.append("same normalized grade")

    return score, list(dict.fromkeys(reasons))


def _alternative_record(record: dict[str, Any], score: float, reasons: list[str]) -> dict[str, Any]:
    return {
        "brand": record.get("brand", ""),
        "series": record.get("series", ""),
        "tool_category": record.get("tool_category", ""),
        "manufacturer_reference": record.get("manufacturer_reference", ""),
        "score": round(score, 2),
        "match_reasons": reasons,
        "search_hint": record.get("search_hint", ""),
    }


def _exact_match_payload(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "brand": record.get("brand", ""),
        "manufacturer_number": record.get("manufacturer_number", ""),
        "manufacturer_reference": record.get("manufacturer_reference", ""),
        "normalized_number": record.get("normalized_number", ""),
        "tool_category": record.get("tool_category", ""),
        "series": record.get("series", ""),
        "designation": record.get("designation", ""),
        "grade": record.get("grade", ""),
        "geometry": record.get("geometry", {}),
        "materials": record.get("materials", {"iso_groups": []}),
        "application": record.get("application", {"operations": [], "strategy": ""}),
        "source_catalog": record.get("source_catalog", ""),
        "search_hint": record.get("search_hint", ""),
    }


def _dedupe_alternatives(scored: list[tuple[float, dict[str, Any], list[str]]]) -> list[tuple[float, dict[str, Any], list[str]]]:
    deduped: dict[tuple[str, str, str, str], tuple[float, dict[str, Any], list[str]]] = {}
    for score, record, reasons in scored:
        key = (
            str(record.get("brand", "")),
            str(record.get("series", "")),
            str(record.get("manufacturer_reference", "")),
            str(record.get("tool_category", "")),
        )
        if key not in deduped or score > deduped[key][0]:
            deduped[key] = (score, record, reasons)
        else:
            existing_score, existing_record, existing_reasons = deduped[key]
            merged_reasons = list(dict.fromkeys(existing_reasons + reasons))
            deduped[key] = (existing_score, existing_record, merged_reasons)
    return sorted(
        deduped.values(),
        key=lambda item: (-item[0], item[1].get("brand", ""), item[1].get("series", "")),
    )


def cross_reference_tool(
    query: str | None,
    tool_category: str | None = None,
    brand: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    normalized_query = normalize_tool_number(query)
    response = {
        "query": query or "",
        "normalized_query": normalized_query,
        "exact_match": None,
        "alternatives": [],
        "warnings": [],
    }
    if not normalized_query:
        response["warnings"].append("No lookup query provided.")
        return response

    records = load_lookup_records()
    filtered = [
        record
        for record in records
        if (not tool_category or record.get("tool_category") == tool_category)
        and (not brand or record.get("brand") == brand)
    ]

    exact_match = _exact_match(filtered, normalized_query)
    if exact_match:
        response["exact_match"] = _exact_match_payload(exact_match)

    seed_profile = _seed_profile(filtered, normalized_query)
    if exact_match:
        seed_profile["iso_groups"].update(_safe_list(exact_match.get("materials", {}).get("iso_groups", [])))
        seed_profile["operations"].update(_safe_list(exact_match.get("application", {}).get("operations", [])))
        if exact_match.get("tool_category"):
            seed_profile["tool_categories"].add(str(exact_match["tool_category"]))
        chipbreaker = exact_match.get("geometry", {}).get("chipbreaker")
        if isinstance(chipbreaker, str) and chipbreaker.strip():
            seed_profile["chipbreakers"].add(chipbreaker.strip().upper())

    query_tokens = parse_tool_number_tokens(normalized_query)
    query_prefixes = _designation_prefixes(normalized_query)
    scored: list[tuple[float, dict[str, Any], list[str]]] = []
    exact_key = None
    if exact_match:
        exact_key = (
            exact_match.get("brand", ""),
            exact_match.get("series", ""),
            exact_match.get("manufacturer_reference", ""),
        )

    for record in filtered:
        record_key = (
            record.get("brand", ""),
            record.get("series", ""),
            record.get("manufacturer_reference", ""),
        )
        if exact_key and record_key == exact_key:
            continue
        score, reasons = _score_record(
            record,
            normalized_query,
            query_tokens,
            query_prefixes,
            seed_profile,
            tool_category,
            brand,
        )
        if score > 0:
            scored.append((score, record, reasons))

    scored = [item for item in scored if item[0] >= 6.0]
    scored = _dedupe_alternatives(scored)
    response["alternatives"] = [
        _alternative_record(record, score, reasons)
        for score, record, reasons in scored[: max(1, limit)]
    ]

    if response["exact_match"] is None:
        response["warnings"].append(
            "No exact manufacturer-number match found. Alternatives are inferred from family, designation, material, and application data."
        )

    return response
