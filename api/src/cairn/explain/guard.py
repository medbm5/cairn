"""Number guard: every number in generated text must come from the facts.

A number is accepted if it matches a value derived from the facts, allowing for the formatting a
person would use: euros instead of cents, thousands ("12k") or millions, percentages instead of
fractions (and their complement, "1 in 4 falls short"), years instead of months, and rounding.
"""

import re
from collections.abc import Iterable

from pydantic import BaseModel

from cairn.domain.stress import Scenario

# Numbers that are labels rather than figures: percentile names in the UI and "one".
ALWAYS_ALLOWED: frozenset[float] = frozenset({1, 10, 50, 90})

SCENARIO_YEARS = {Scenario.GFC_2008: 2008, Scenario.COVID_2020: 2020, Scenario.RATES_2022: 2022}

# A grouped number ("12 000", "6,595.70", "1.250.000,5") or a plain one ("75.8", "75,8", "2040").
SEPARATORS = " \u00a0\u202f'"  # space, no-break space, narrow no-break space
NUMBER = re.compile(
    rf"(?<![\d])(?:\d{{1,3}}(?:[{SEPARATORS},.]\d{{3}})+(?:[.,]\d+)?|\d+(?:[.,]\d+)?)(?![\d])"
)


def parse_number(token: str) -> float:
    """Read a number written in English or French style."""
    token = re.sub(f"[{SEPARATORS}]", "", token)
    if "," in token and "." in token:
        decimal = "," if token.rfind(",") > token.rfind(".") else "."
        thousands = "." if decimal == "," else ","
        token = token.replace(thousands, "").replace(decimal, ".")
    elif token.count(",") > 1 or token.count(".") > 1:
        token = token.replace(",", "").replace(".", "")
    elif "," in token or "." in token:
        sep = "," if "," in token else "."
        before, after = token.split(sep)
        # "12,000" or "12.000" is a thousands group; "75,8" or "6.5" is a decimal.
        token = before + after if len(after) == 3 else f"{before}.{after}"
    return float(token)


def numbers_in(text: str) -> list[float]:
    return [parse_number(match) for match in NUMBER.findall(text)]


def _derived(name: str, value: object) -> Iterable[float]:
    if isinstance(value, bool) or value is None:
        return
    if isinstance(value, Scenario):
        yield SCENARIO_YEARS[value]
    elif isinstance(value, dict):
        for item in value.values():
            yield from _derived("fraction", item)
    elif isinstance(value, list):
        return
    elif isinstance(value, int) and name.endswith("_cents"):
        euros = value / 100
        yield from (euros, euros / 1_000, euros / 1_000_000)
    elif isinstance(value, int) and "months" in name:
        yield from (value, value / 12)
    elif isinstance(value, int):
        yield value
    elif isinstance(value, float):
        yield from (value * 100, (1 - value) * 100, value)


def allowed_numbers(facts: BaseModel) -> list[float]:
    allowed = list(ALWAYS_ALLOWED)
    for name in type(facts).model_fields:
        allowed.extend(_derived(name, getattr(facts, name)))
    return allowed


def _matches(number: float, allowed: Iterable[float]) -> bool:
    return any(abs(number - a) <= max(0.51, 0.01 * abs(a)) for a in allowed)


def unknown_numbers(text: str, facts: BaseModel | None) -> list[float]:
    """Numbers in the text that the facts do not account for."""
    allowed = allowed_numbers(facts) if facts is not None else list(ALWAYS_ALLOWED)
    return [n for n in numbers_in(text) if not _matches(n, allowed)]
