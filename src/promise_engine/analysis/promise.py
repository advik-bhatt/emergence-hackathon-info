"""The per-order promise: handling (the seller's part) + transit (the lane's part).

    promise(seller, state)                       = handling_p95(seller) + transit_p95(state)
    promise(seller, state, month, seasonal=True)  = handling_p95(seller)
                                                     + transit_p95(state) * season_factor(month)

transit_p95 comes from the state_transit fixture (carrier handoff -> customer), NOT the lanes
fixture (purchase -> customer, which already bakes in handling). Using the lane's p95 here
would double-count handling. For RJ this decomposition reconciles with the lane's own
end-to-end number: handling 5.0 (median seller) + transit 34.0 = 39, vs the lane's p95 of 38.

Seasonality is opt-in and off by default: the base promise is a pure two-term decomposition,
and when the caller does opt in, the seasonal contribution appears as its own attribution
line (Quote.season_days) rather than being folded silently into the total.
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import median
from typing import Any

from promise_engine.analysis.lanes import load_lanes
from promise_engine.analysis.season import SeasonModel
from promise_engine.analysis.verdict import Verdict
from promise_engine.craft.cassette import Cassette
from promise_engine.models import Lane

# A seller needs this many delivered items before we trust their handling p95. The
# seller_handling fixture is already filtered to this threshold (all 461 rows qualify); we
# re-check here so the loader is correct even against a re-record that isn't pre-filtered.
MIN_DELIVERED_ITEMS = 50

SELLER_ALIASES: dict[str, list[str]] = {
    "seller_id": ["seller_id"],
    "p95_handling_days": ["p95_handling_days"],
    "median_handling_days": ["median_handling_days"],
    "delivered_items": ["delivered_items", "delivered_items_count"],
}

TRANSIT_ALIASES: dict[str, list[str]] = {
    "state": ["customer_state", "state", "delivery_state"],
    "p95_transit_days": ["p95_carrier_transit_days", "p95_transit_days"],
    "median_transit_days": ["median_carrier_transit_days", "median_transit_days"],
}


def _resolve(row: dict[str, Any], aliases: dict[str, list[str]], concept: str) -> Any:
    for alias in aliases[concept]:
        if alias in row:
            return row[alias]
    raise KeyError(
        f"Could not find a column for {concept!r} among {sorted(row.keys())}. "
        f"Extend the alias table in promise_engine/analysis/promise.py."
    )


@dataclass(frozen=True)
class SellerHandling:
    seller_id: str
    p95_handling_days: float
    median_handling_days: float
    delivered_items: int


@dataclass(frozen=True)
class StateTransit:
    state: str
    p95_transit_days: float
    median_transit_days: float


@dataclass(frozen=True)
class Quote:
    seller_id: str
    state: str
    handling_days: float
    transit_days: float
    season_factor: float
    handling_is_fallback: bool
    lane: Lane
    transit_median_days: float

    @property
    def season_days(self) -> float:
        """The seasonal attribution line: zero unless the caller opted in."""
        return self.transit_days * (self.season_factor - 1.0)

    @property
    def days(self) -> float:
        return self.handling_days + self.transit_days * self.season_factor

    @property
    def current_promise(self) -> float:
        return self.lane.promised_days

    @property
    def verdict(self) -> Verdict:
        return self.lane.verdict

    @property
    def transit_tail_days(self) -> float:
        """The recoverable part of transit: tail, not distance."""
        return self.transit_days - self.transit_median_days


def _load_seller_handling(result) -> dict[str, SellerHandling]:
    handling: dict[str, SellerHandling] = {}
    for row in result.as_dicts():
        items = int(_resolve(row, SELLER_ALIASES, "delivered_items"))
        if items < MIN_DELIVERED_ITEMS:
            continue
        seller_id = str(_resolve(row, SELLER_ALIASES, "seller_id"))
        handling[seller_id] = SellerHandling(
            seller_id=seller_id,
            p95_handling_days=float(_resolve(row, SELLER_ALIASES, "p95_handling_days")),
            median_handling_days=float(_resolve(row, SELLER_ALIASES, "median_handling_days")),
            delivered_items=items,
        )
    return handling


def _load_state_transit(result) -> dict[str, StateTransit]:
    transit: dict[str, StateTransit] = {}
    for row in result.as_dicts():
        state = str(_resolve(row, TRANSIT_ALIASES, "state"))
        transit[state] = StateTransit(
            state=state,
            p95_transit_days=float(_resolve(row, TRANSIT_ALIASES, "p95_transit_days")),
            median_transit_days=float(_resolve(row, TRANSIT_ALIASES, "median_transit_days")),
        )
    return transit


@dataclass
class PromiseEngine:
    lanes: dict[str, Lane]
    seller_handling: dict[str, SellerHandling]
    transit: dict[str, StateTransit]
    season_model: SeasonModel
    national_median_handling_p95: float

    @classmethod
    def from_cassette(cls, cassette: Cassette) -> PromiseEngine:
        lanes = {lane.state: lane for lane in load_lanes(cassette.replay("lanes"))}
        seller_handling = _load_seller_handling(cassette.replay("seller_handling"))
        transit = _load_state_transit(cassette.replay("state_transit"))
        season_model = SeasonModel.from_cassette(cassette)
        national_median_handling_p95 = (
            median(h.p95_handling_days for h in seller_handling.values())
            if seller_handling else 0.0
        )
        return cls(
            lanes=lanes,
            seller_handling=seller_handling,
            transit=transit,
            season_model=season_model,
            national_median_handling_p95=national_median_handling_p95,
        )

    def any_seller(self) -> str:
        """Test helper: an arbitrary known seller_id."""
        return next(iter(self.seller_handling))

    def quote(
        self,
        *,
        seller_id: str,
        state: str,
        month: int | None = None,
        seasonal: bool = False,
    ) -> Quote:
        if state not in self.transit or state not in self.lanes:
            raise KeyError(f"No lane data for state {state!r}.")

        handling = self.seller_handling.get(seller_id)
        if handling is None:
            handling_days = self.national_median_handling_p95
            handling_is_fallback = True
        else:
            handling_days = handling.p95_handling_days
            handling_is_fallback = False

        transit = self.transit[state]
        season_factor = self.season_model.factor(month) if seasonal else 1.0

        return Quote(
            seller_id=seller_id,
            state=state,
            handling_days=handling_days,
            transit_days=transit.p95_transit_days,
            season_factor=season_factor,
            handling_is_fallback=handling_is_fallback,
            lane=self.lanes[state],
            transit_median_days=transit.median_transit_days,
        )
