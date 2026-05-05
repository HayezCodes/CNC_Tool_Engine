from __future__ import annotations

import re


SEPARATOR_PATTERN = re.compile(r"[\s\-_/]+")
NON_ALNUM_PATTERN = re.compile(r"[^A-Z0-9]")


def normalize_tool_number(value: str | None) -> str:
    if not isinstance(value, str):
        return ""
    normalized = value.upper().strip()
    normalized = SEPARATOR_PATTERN.sub("", normalized)
    normalized = NON_ALNUM_PATTERN.sub("", normalized)
    return normalized
