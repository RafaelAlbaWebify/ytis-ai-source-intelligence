from __future__ import annotations

from typing import Any


def as_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(str(value).replace(",", "").strip()))
    except Exception:
        return default


def compact_number(value: Any, plus: bool = False) -> str:
    """Return dashboard-safe compact numbers.

    Examples:
    70454 -> 70.5k
    1850  -> 1.9k
    46    -> 46

    plus=True gives +70.5k for labels that represent volume.
    """
    number = as_int(value)
    prefix = "+" if plus and number > 0 else ""

    abs_number = abs(number)
    if abs_number >= 1_000_000:
        formatted = f"{number / 1_000_000:.1f}M"
    elif abs_number >= 10_000:
        formatted = f"{number / 1_000:.1f}k"
    elif abs_number >= 1_000:
        formatted = f"{number / 1_000:.1f}k"
    else:
        formatted = f"{number:,}"

    formatted = formatted.replace(".0k", "k").replace(".0M", "M")
    return prefix + formatted


def full_number(value: Any) -> str:
    return f"{as_int(value):,}"
