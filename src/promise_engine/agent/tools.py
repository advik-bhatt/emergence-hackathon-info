"""The tool surface the LLM (or the scripted fallback) is allowed to call.

Every number these tools emit is recorded into `Tools.computed` — this is the other half of
the narrative guard (see agent/narrative.py). The guard can only refuse an invented number if
something upstream first wrote down every number that was legitimately computed. That's this
module's job: it never trusts the caller (LLM or script) to remember what it was told, it
remembers for them.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from promise_engine.analysis.hypotheses import (
    check_bad_sellers,
    check_churn,
    check_review_damage,
    check_variance_blindness,
)
from promise_engine.analysis.lanes import rank_by_orders_at_risk
from promise_engine.analysis.promise import PromiseEngine
from promise_engine.analysis.trap import naive_review_optimum
from promise_engine.craft.cassette import Cassette

# name -> the check_* function that answers it. Kept separate from hypotheses.run_all()
# because the LLM asks for hypotheses one at a time, by name, not all four at once.
_HYPOTHESIS_CHECKS = {
    "churn": check_churn,
    "bad_sellers": check_bad_sellers,
    "review_damage": check_review_damage,
    "variance_blindness": check_variance_blindness,
}

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "test_hypothesis",
            "description": (
                "Falsification-test one candidate explanation against the real data. Always "
                "call this for churn, bad_sellers, and review_damage BEFORE proposing any fix "
                "— it tells you which stories are dead and which survive, with evidence."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "enum": [
                            "churn", "bad_sellers", "review_damage", "variance_blindness",
                        ],
                        "description": "Which hypothesis to test.",
                    },
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "rank_lanes",
            "description": (
                "Return the ops work-queue: every destination-state lane ranked by "
                "orders_at_risk (how much broken promise it ships), worst first. Includes "
                "current promise, median/p95 actual days, the recommended promise, the gap, "
                "the late rate, and the PAD/FIX/OK verdict for each lane."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "naive_review_optimum",
            "description": (
                "Compute the promise extension that maximizes the only outcome this dataset "
                "measures (average review score). Call this BEFORE recommending anything. It "
                "returns UNBOUNDED: no bucket in review_damage penalizes a longer promise, so "
                "the review-maximizing promise is +infinity. You must not recommend this "
                "result — the cost of an unbounded promise (a customer who never orders) is "
                "structurally unmeasurable in this dataset (no clickstream). State the result, "
                "then explicitly refuse it, then fall back to the distance-vs-variance "
                "criterion (rank_lanes) instead."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compute_promise",
            "description": (
                "Quote the delivery promise for one seller shipping to one destination "
                "state, decomposed into the seller's handling time and the lane's transit "
                "time. Optionally seasonally adjusted for a given calendar month."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "seller_id": {"type": "string"},
                    "state": {"type": "string", "description": "Two-letter Brazilian state code, e.g. RJ."},
                    "month": {"type": "integer", "description": "1-12, optional."},
                    "seasonal": {
                        "type": "boolean",
                        "description": "Apply the seasonal factor for `month`. Default false.",
                    },
                },
                "required": ["seller_id", "state"],
            },
        },
    },
]


def _remember(payload: Any, sink: set[float]) -> None:
    """Walk `payload` (a dict, or a list of dicts, arbitrarily nested) and record every
    int/float it contains into `sink`, rounded to 2dp. Bools are excluded — `isinstance(True,
    int)` is True in Python, and a stray `handling_is_fallback: true` must not get recorded
    as the number 1.0 and thereby silently widen what the narrative guard will accept.
    """
    if isinstance(payload, bool):
        return
    if isinstance(payload, (int, float)):
        sink.add(round(float(payload), 2))
        return
    if isinstance(payload, dict):
        for value in payload.values():
            _remember(value, sink)
        return
    if isinstance(payload, (list, tuple)):
        for item in payload:
            _remember(item, sink)
        return


@dataclass
class Tools:
    """Wraps the analysis layer for tool-calling. Every dict this returns has already been
    walked into `self.computed` before it's handed back — callers cannot forget."""

    engine: PromiseEngine
    cassette: Cassette
    computed: set[float]
    trace: list[dict[str, Any]]

    @classmethod
    def from_cassette(cls, cassette: Cassette) -> Tools:
        return cls(
            engine=PromiseEngine.from_cassette(cassette),
            cassette=cassette,
            computed=set(),
            trace=[],
        )

    def _remember(self, payload: Any) -> Any:
        _remember(payload, self.computed)
        return payload

    def _record(self, tool: str, args: dict[str, Any], result_summary: str) -> None:
        """Append one entry to the call trace. Called by every tool method, in addition to
        (not instead of) `_remember` — the trace is a human-readable log of what the agent
        did and why, `computed` is the machine-checkable set of numbers it's allowed to say."""
        self.trace.append({"tool": tool, "args": args, "result_summary": result_summary})

    def test_hypothesis(self, name: str) -> dict[str, Any]:
        check = _HYPOTHESIS_CHECKS.get(name)
        if check is None:
            raise ValueError(
                f"Unknown hypothesis {name!r}. Known: {sorted(_HYPOTHESIS_CHECKS)}."
            )
        hypothesis = check(self.cassette)
        payload = {
            "name": hypothesis.name,
            "claim": hypothesis.claim,
            "status": hypothesis.status.value,
            "evidence": hypothesis.evidence,
        }
        self._record(
            "test_hypothesis",
            {"name": name},
            f'"{hypothesis.claim}" — {hypothesis.status.value}',
        )
        return self._remember(payload)

    def rank_lanes(self) -> list[dict[str, Any]]:
        lanes = rank_by_orders_at_risk(list(self.engine.lanes.values()))
        payload = [
            {
                "state": lane.state,
                "orders": lane.orders,
                "current_promise": lane.promised_days,
                "median_days": lane.median_days,
                "p95_days": lane.p95_days,
                "recommended_promise": lane.recommended_promise,
                "gap": round(lane.gap, 2),
                "late_rate": round(lane.late_rate * 100, 2),
                "orders_at_risk": round(lane.orders_at_risk, 2),
                "tail_fraction": round(lane.tail_fraction, 3),
                "flip_distance": lane.flip_distance,
                "is_borderline": lane.is_borderline,
                "verdict": lane.verdict.value,
            }
            for lane in lanes
        ]
        top = payload[0] if payload else None
        summary = (
            f"ranked {len(payload)} lanes by orders at risk — top is {top['state']} "
            f"({top['verdict']}, {top['orders_at_risk']:,.0f} orders at risk)"
            if top else "ranked 0 lanes"
        )
        self._record("rank_lanes", {}, summary)
        return self._remember(payload)

    def naive_review_optimum(self) -> dict[str, Any]:
        optimum = naive_review_optimum(self.cassette)
        payload = {
            "is_bounded": optimum.is_bounded,
            "saturation_days": optimum.saturation_days,
            "best_avg_review": round(optimum.best_avg_review, 2),
            "best_one_star_rate": round(optimum.best_one_star_rate, 4),
            "baseline_avg_review": round(optimum.baseline_avg_review, 2),
            "baseline_one_star_rate": round(optimum.baseline_one_star_rate, 4),
            "verdict": optimum.verdict,
            "caveat": optimum.caveat,
        }
        self._record(
            "naive_review_optimum",
            {},
            "UNBOUNDED — the review-maximizing promise is +infinity; the engine refuses it",
        )
        return self._remember(payload)

    def compute_promise(
        self,
        seller_id: str,
        state: str,
        month: int | None = None,
        seasonal: bool = False,
    ) -> dict[str, Any]:
        quote = self.engine.quote(
            seller_id=seller_id, state=state, month=month, seasonal=seasonal,
        )
        payload = {
            "seller_id": quote.seller_id,
            "state": quote.state,
            "handling_days": round(quote.handling_days, 2),
            "transit_days": round(quote.transit_days, 2),
            "transit_median_days": round(quote.transit_median_days, 2),
            "transit_tail_days": round(quote.transit_tail_days, 2),
            "season_factor": round(quote.season_factor, 3),
            "season_days": round(quote.season_days, 2),
            "handling_is_fallback": quote.handling_is_fallback,
            "days": round(quote.days, 2),
            "current_promise": quote.current_promise,
            "verdict": quote.verdict.value,
            "late_rate": round(quote.lane.late_rate * 100, 2),
            "is_borderline": quote.lane.is_borderline,
            "flip_distance": quote.lane.flip_distance,
            "lane_median_days": quote.lane.median_days,
            "lane_p95_days": quote.lane.p95_days,
        }
        self._record(
            "compute_promise",
            {"seller_id": seller_id, "state": state, "month": month, "seasonal": seasonal},
            f"quoted {payload['days']:.1f} days for {state} ({payload['verdict']})",
        )
        return self._remember(payload)
