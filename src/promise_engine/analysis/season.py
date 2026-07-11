"""Whether the promise should flex with the calendar.

Fit on ~2 years of data and a single Black Friday, this model is opt-in everywhere it is
used (see promise.py): the caller must ask for it explicitly, and it always shows up as its
own attribution line rather than being folded silently into a total.

The factor for a month is that month's mean actual-delivery-days divided by the median across
all months, clamped to [MIN_FACTOR, MAX_FACTOR] so a thin month can't produce an absurd quote.
A month we have no data for is neutral (factor 1.0) rather than an error — the caller may ask
about any calendar month, not just the ones in the fixture.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from statistics import median
from typing import Any

from promise_engine.craft.cassette import Cassette

# A thin or noisy month cannot swing the quote beyond this band.
MIN_FACTOR = 0.8
MAX_FACTOR = 1.5

# concept -> acceptable column names, resolved the same way analysis/lanes.py does: by intent,
# not by hard-coding today's exact CRAFT column name.
ALIASES: dict[str, list[str]] = {
    "month": ["order_month", "month"],
    "actual_days": [
        "avg_actual_delivery_days", "actual_delivery_days", "avg_actual_days",
    ],
}


def _resolve(row: dict[str, Any], concept: str) -> Any:
    for alias in ALIASES[concept]:
        if alias in row:
            return row[alias]
    raise KeyError(
        f"Could not find a column for {concept!r} among {sorted(row.keys())}. "
        f"Extend ALIASES in promise_engine/analysis/season.py."
    )


@dataclass(frozen=True)
class SeasonModel:
    factors: dict[int, float]

    def factor(self, month: int | None) -> float:
        """Neutral (1.0) for months we have no data for, or when no month is given."""
        if month is None:
            return 1.0
        return self.factors.get(month, 1.0)

    @classmethod
    def from_cassette(cls, cassette: Cassette) -> SeasonModel:
        result = cassette.replay("seasonality")
        by_month: dict[int, list[float]] = defaultdict(list)
        for row in result.as_dicts():
            month = int(_resolve(row, "month"))
            actual_days = float(_resolve(row, "actual_days"))
            by_month[month].append(actual_days)

        means = {month: sum(days) / len(days) for month, days in by_month.items()}
        overall_median = median(means.values()) if means else 0.0

        factors = {}
        for month, mean_days in means.items():
            raw = mean_days / overall_median if overall_median else 1.0
            factors[month] = min(MAX_FACTOR, max(MIN_FACTOR, raw))
        return cls(factors=factors)
