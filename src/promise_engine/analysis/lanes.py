"""Load Lane objects out of a CRAFT query result.

generate_sql is free to rename a column on a re-record (AVG_PROMISED_DAYS today might come
back AVERAGE_PROMISED_DAYS tomorrow), so we resolve columns by *intent* — a small alias table
mapping each concept we need to the set of column names we've seen or expect to see for it —
rather than hard-coding the exact strings from one recording. If a concept can't be resolved
at all, we raise a clear error naming the missing concept instead of silently misreading a
column or crashing with a bare KeyError deep in dataclass construction.
"""

from __future__ import annotations

from typing import Any

from promise_engine.craft.cassette import QueryResult
from promise_engine.models import Lane

# concept -> acceptable column names (as returned by QueryResult.as_dicts(), i.e. lowercased).
# Extend this table when a re-record renames a column instead of hard-coding the new name
# somewhere else.
ALIASES: dict[str, list[str]] = {
    "state": ["customer_state", "state", "delivery_state", "customer_state_code"],
    "orders": ["order_count", "orders", "num_orders", "total_orders", "order_cnt"],
    "promised_days": [
        "avg_promised_days", "average_promised_days", "promised_days", "avg_promise_days",
    ],
    "median_days": [
        "median_actual_days", "median_days", "median_delivery_days",
        "median_actual_delivery_days",
    ],
    "p95_days": [
        "p95_actual_days", "p95_days", "p95_actual_delivery_days", "percentile_95_days",
    ],
    "late_rate_pct": ["late_rate_pct", "late_rate", "late_rate_percent", "pct_late"],
}


def _resolve(row: dict[str, Any], concept: str) -> Any:
    for alias in ALIASES[concept]:
        if alias in row:
            return row[alias]
    raise KeyError(
        f"Could not find a column for {concept!r} among {sorted(row.keys())}. "
        f"Extend ALIASES in promise_engine/analysis/lanes.py."
    )


def _normalize_late_rate(value: float) -> float:
    """CRAFT returns 13.47 meaning percent. We store 0.1347."""
    return value / 100 if value > 1 else value


def load_lanes(result: QueryResult) -> list[Lane]:
    lanes = []
    for row in result.as_dicts():
        lanes.append(
            Lane(
                state=str(_resolve(row, "state")),
                orders=int(_resolve(row, "orders")),
                promised_days=float(_resolve(row, "promised_days")),
                median_days=float(_resolve(row, "median_days")),
                p95_days=float(_resolve(row, "p95_days")),
                late_rate=_normalize_late_rate(float(_resolve(row, "late_rate_pct"))),
            )
        )
    return lanes


def rank_by_orders_at_risk(lanes) -> list[Lane]:
    """Ops work queue: lanes ordered by how much broken promise they ship, worst first."""
    return sorted(lanes, key=lambda lane: lane.orders_at_risk, reverse=True)
