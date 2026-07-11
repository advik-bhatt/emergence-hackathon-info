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


def _resolve(row: dict[str, Any], concept: str) -> tuple[str, Any]:
    """Return (matched_alias, value) — callers that need to know the unit a value was
    expressed in (see _normalize_late_rate) must not throw away which column matched."""
    for alias in ALIASES[concept]:
        if alias in row:
            return alias, row[alias]
    raise KeyError(
        f"Could not find a column for {concept!r} among {sorted(row.keys())}. "
        f"Extend ALIASES in promise_engine/analysis/lanes.py."
    )


def _normalize_late_rate(alias: str, value: float) -> float:
    """Decide the UNIT from the matched COLUMN NAME, never from the magnitude of the value.

    A magnitude check (`value / 100 if value > 1 else value`) is unfixable in general: a
    genuine fraction can never exceed 1, but a genuine percent absolutely can be below 1
    (e.g. a lane with a real late rate of 0.85% arrives as the float 0.85). That case fails
    `> 1`, and the value is stored unchanged as 0.85 — silently read as 85% late instead of
    0.85% late. The column name, not the number, tells us the unit.
    """
    is_percent = alias.endswith("_pct") or alias.endswith("_percent") or alias == "pct_late"
    late_rate = value / 100 if is_percent else value
    if not 0.0 <= late_rate <= 1.0:
        raise ValueError(
            f"late_rate {late_rate!r} (from column {alias!r}, raw value {value!r}) is "
            f"outside the valid range [0.0, 1.0]. This means the column matched the wrong "
            f"concept, or the source data is corrupt — refusing to silently store it."
        )
    return late_rate


def load_lanes(result: QueryResult) -> list[Lane]:
    lanes = []
    for row in result.as_dicts():
        _, state = _resolve(row, "state")
        _, orders = _resolve(row, "orders")
        _, promised_days = _resolve(row, "promised_days")
        _, median_days = _resolve(row, "median_days")
        _, p95_days = _resolve(row, "p95_days")
        late_alias, late_raw = _resolve(row, "late_rate_pct")
        lanes.append(
            Lane(
                state=str(state),
                orders=int(orders),
                promised_days=float(promised_days),
                median_days=float(median_days),
                p95_days=float(p95_days),
                late_rate=_normalize_late_rate(late_alias, float(late_raw)),
            )
        )
    return lanes


def rank_by_orders_at_risk(lanes) -> list[Lane]:
    """Ops work queue: lanes ordered by how much broken promise they ship, worst first."""
    return sorted(lanes, key=lambda lane: lane.orders_at_risk, reverse=True)
