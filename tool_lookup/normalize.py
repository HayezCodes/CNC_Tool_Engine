from __future__ import annotations

import re


SEPARATOR_PATTERN = re.compile(r"[\s\-_/]+")
NON_ALNUM_PATTERN = re.compile(r"[^A-Z0-9]")
SIZE_TOKEN_PATTERN = re.compile(r"^\d{3,4}")
GRADE_TOKEN_PATTERN = re.compile(r"\d{4}$")

KNOWN_DESIGNATION_PREFIXES = tuple(
    sorted(
        {
            "CNMG",
            "DNMG",
            "VNMG",
            "WNMG",
            "SNMG",
            "TNMG",
            "RNMG",
            "CCMT",
            "DCMT",
            "VBMT",
            "VCMT",
            "TCMT",
            "CCGW",
            "16ER",
            "16IR",
            "COROMILL",
            "CORODRILL",
            "COROCUT",
            "COROTHREAD",
        },
        key=len,
        reverse=True,
    )
)

KNOWN_SUFFIX_TOKENS = tuple(
    sorted(
        {
            "MRR",
            "AG60",
            "AG55",
            "PF",
            "PR",
            "MF",
            "MR",
            "SM",
            "WF",
            "XF",
        },
        key=len,
        reverse=True,
    )
)


def normalize_tool_number(value: str | None) -> str:
    if not isinstance(value, str):
        return ""
    normalized = value.upper().strip()
    normalized = SEPARATOR_PATTERN.sub("", normalized)
    normalized = NON_ALNUM_PATTERN.sub("", normalized)
    return normalized


def _designation_prefix(normalized_value: str) -> str:
    for prefix in KNOWN_DESIGNATION_PREFIXES:
        if normalized_value.startswith(prefix):
            return prefix
    if normalized_value[:4].isalpha():
        return normalized_value[:4]
    return ""


def parse_tool_number_tokens(value: str | None) -> dict[str, str]:
    normalized = normalize_tool_number(value)
    tokens = {
        "normalized": normalized,
        "designation_prefix": "",
        "size_token": "",
        "suffix_token": "",
        "grade_token": "",
    }
    if not normalized:
        return tokens

    designation_prefix = _designation_prefix(normalized)
    tokens["designation_prefix"] = designation_prefix
    remainder = normalized[len(designation_prefix):] if designation_prefix else normalized

    grade_match = GRADE_TOKEN_PATTERN.search(remainder)
    if grade_match:
        tokens["grade_token"] = grade_match.group(0)
        remainder = remainder[: -len(tokens["grade_token"])]

    size_match = SIZE_TOKEN_PATTERN.match(remainder)
    if size_match:
        tokens["size_token"] = size_match.group(0)
        remainder = remainder[len(tokens["size_token"]):]

    for suffix in KNOWN_SUFFIX_TOKENS:
        if remainder.endswith(suffix):
            tokens["suffix_token"] = suffix
            remainder = remainder[: -len(suffix)]
            break

    if not tokens["suffix_token"] and remainder:
        tokens["suffix_token"] = remainder

    return tokens
