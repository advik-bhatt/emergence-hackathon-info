"""The narrative guard: the LLM cannot state a number the analysis layer didn't compute.

If the model invents a delivery date, a late rate, an order count — anything numeric that
didn't come out of the fixtures via the analysis layer — we fail loudly rather than let a
plausible-sounding hallucination reach a customer-facing promise.
"""

from __future__ import annotations

import re

# Numeric literals, in the order they must be tried:
#   1. thousands-separated integers, optionally with a decimal tail ("12,350", "12,350.5")
#   2. plain decimals ("38.02")
#   3. plain integers ("41")
# The lookbehind/lookahead keep us from pulling a stray number out of an alphanumeric token
# like "p95" or "RJ2" — this is a domain that says "p95" constantly, and that "95" is not a
# data claim.
_NUMBER_RE = re.compile(
    r"(?<![A-Za-z0-9])(?:\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+\.\d+|\d+)(?![A-Za-z])"
)

# Small counting/rhetoric integers that show up in prose without being data claims:
# "two options", "1 in 7", "95% on-time", "100%". Not exhaustive — just the common ones.
ALLOWED_PROSE_NUMBERS: frozenset[float] = frozenset(
    float(n) for n in [*range(0, 8), 10, 95, 100]
)

# A stated number within this many days/units of a computed value is a rounding, not an
# invention: computing 38.02 and saying "38" must not trip the guard.
ROUNDING_TOLERANCE = 0.55


class HallucinatedNumber(ValueError):
    """The model stated a figure the analysis layer never produced."""


def extract_numbers(text: str) -> set[float]:
    """All numeric literals in `text`, with thousands separators stripped."""
    return {float(match.group().replace(",", "")) for match in _NUMBER_RE.finditer(text)}


def check_numbers(text: str, allowed: set[float]) -> None:
    """Raise HallucinatedNumber if `text` states a figure not in `allowed`.

    A number is accepted if it's one of the small prose integers, or if it's within
    ROUNDING_TOLERANCE of something in `allowed`. Everything else is treated as an invented
    data claim.
    """
    for number in extract_numbers(text):
        if number in ALLOWED_PROSE_NUMBERS:
            continue
        if any(abs(number - value) <= ROUNDING_TOLERANCE for value in allowed):
            continue
        raise HallucinatedNumber(
            f"The model stated {number!r}, which the analysis layer never computed. "
            f"Computed values were: {sorted(allowed)}."
        )
