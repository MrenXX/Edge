"""Coerce French / formatted numeric strings from LLM JSON into floats."""

from __future__ import annotations

import re
from typing import Any


_NUMISH = re.compile(r"^[\d\s.,+\-]+$")


def to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return None
    s = value.strip().replace("\u00a0", " ").replace(" ", "")
    if not s or s.lower() == "null":
        return None
    if not _NUMISH.match(s.replace(".", "").replace(",", "")):
        return None
    # Decimal comma vs thousands: if exactly one comma and short fractional part -> decimal comma
    if "," in s and "." not in s:
        parts = s.split(",")
        if len(parts) == 2 and 0 < len(parts[1]) <= 3:
            s = parts[0] + "." + parts[1]
        else:
            s = s.replace(",", "")
    else:
        s = s.replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


def normalize_numbers(obj: Any) -> None:
    """In-place: turn numeric-looking strings into floats inside dict/list trees."""
    if isinstance(obj, dict):
        for k, v in list(obj.items()):
            if isinstance(v, (dict, list)):
                normalize_numbers(v)
            elif isinstance(v, str):
                f = to_float(v)
                if f is not None:
                    obj[k] = f
    elif isinstance(obj, list):
        for item in obj:
            normalize_numbers(item)
