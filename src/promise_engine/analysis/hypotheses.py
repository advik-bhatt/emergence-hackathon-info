"""The falsification suite.

This is what makes the agent investigate rather than report. Each hypothesis is checked
against the fixtures and comes back SURVIVES or DEAD, with evidence computed from the data
at run time — nothing here is a hardcoded number, only the thresholds that decide the verdict.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from promise_engine.analysis.lanes import load_lanes
from promise_engine.analysis.verdict import Verdict
from promise_engine.craft.cassette import Cassette

# churn: a real churn signal would show 1-star customers repeating far less than 5-star
# customers. Below this spread (in percentage points) there is no signal, only noise.
CHURN_DEAD_SPREAD_PP = 1.0

# bad_sellers: "a few terrible sellers" requires at least one seller actually being terrible.
BAD_SELLER_LATE_RATE_PCT = 40.0

# review_damage: SURVIVES if the average review score collapses by more than this across
# delivery-lateness buckets.
REVIEW_DAMAGE_SPREAD = 1.5


class Status(str, Enum):
    SURVIVES = "SURVIVES"
    DEAD = "DEAD"


@dataclass(frozen=True)
class Hypothesis:
    name: str
    claim: str
    status: Status
    evidence: str


def check_churn(cassette: Cassette) -> Hypothesis:
    """'Bad delivery drives customers away.' The hypothesis the hackathon guide itself
    suggested — it is false, and saying so is the point."""
    rows = cassette.replay("churn").as_dicts()
    overall = next(r for r in rows if str(r["first_order_review_score"]) == "Overall")
    by_score = {
        str(r["first_order_review_score"]): float(r["repeat_purchase_rate_pct"])
        for r in rows
        if str(r["first_order_review_score"]) != "Overall"
    }
    spread = max(by_score.values()) - min(by_score.values())
    status = Status.DEAD if spread < CHURN_DEAD_SPREAD_PP else Status.SURVIVES
    evidence = (
        f"Overall repeat purchase rate is {float(overall['repeat_purchase_rate_pct']):.2f}%. "
        f"Across first-order review scores 1-5 the repeat rate only ranges from "
        f"{min(by_score.values()):.2f}% to {max(by_score.values()):.2f}% — a spread of "
        f"{spread:.2f} percentage points. A real churn signal would show 1-star customers "
        f"repeating far less than 5-star customers; this spread is flat noise, not a signal."
    )
    return Hypothesis(
        name="churn",
        claim="Bad delivery drives customers away",
        status=status,
        evidence=evidence,
    )


def check_bad_sellers(cassette: Cassette) -> Hypothesis:
    """'A few terrible sellers cause the lateness.' Also false — they're big, not bad."""
    row = cassette.replay("seller_lateness").as_dicts()[0]
    baseline = float(row["overall_baseline_late_rate_pct"])
    highest = float(row["highest_seller_late_rate_pct"])
    above_threshold = int(row["sellers_above_40pct"])
    top30_combined = float(row["top30_late_sellers_combined_late_rate_pct"])
    status = Status.DEAD if above_threshold == 0 else Status.SURVIVES
    evidence = (
        f"Baseline late rate across all qualifying sellers is {baseline:.2f}%. The single "
        f"worst seller only reaches {highest:.1f}% late, and {above_threshold} sellers "
        f"exceed {BAD_SELLER_LATE_RATE_PCT:.0f}% late. The top 30 sellers ranked by late-item "
        f"COUNT are just {top30_combined:.2f}% late combined — barely above the "
        f"{baseline:.2f}% baseline. They rank highly because they are big, not bad: this is "
        f"a volume artifact. Lateness is diffuse across the seller base; you cannot fire "
        f"your way out of it."
    )
    return Hypothesis(
        name="bad_sellers",
        claim="A few terrible sellers cause the lateness",
        status=status,
        evidence=evidence,
    )


def check_review_damage(cassette: Cassette) -> Hypothesis:
    """'Breaking the delivery promise destroys reviews.' Survives."""
    rows = cassette.replay("review_damage").as_dicts()
    early = next(r for r in rows if str(r["delivery_bucket"]).lower() == "early")
    worst = min(rows, key=lambda r: float(r["avg_review_score"]))
    early_score = float(early["avg_review_score"])
    worst_score = float(worst["avg_review_score"])
    spread = early_score - worst_score
    status = Status.SURVIVES if spread > REVIEW_DAMAGE_SPREAD else Status.DEAD
    evidence = (
        f"Average review score falls from {early_score:.2f} for early deliveries to "
        f"{worst_score:.2f} in the worst bucket ({worst['delivery_bucket']}) — a spread of "
        f"{spread:.2f}. 1-star review share rises from {float(early['pct_1_star_reviews']):.1f}% "
        f"to {float(worst['pct_1_star_reviews']):.1f}%. Breaking the promise does real, "
        f"measurable damage to reviews."
    )
    return Hypothesis(
        name="review_damage",
        claim="Breaking the delivery promise destroys reviews",
        status=status,
        evidence=evidence,
    )


def check_variance_blindness(cassette: Cassette) -> Hypothesis:
    """'The promise is adjusted for distance, but not for variance.' Survives if some lanes
    are already calibrated (OK) and some are failing on tail alone (FIX)."""
    lanes = load_lanes(cassette.replay("lanes"))
    fix_lanes = [lane for lane in lanes if lane.verdict is Verdict.FIX]
    ok_lanes = [lane for lane in lanes if lane.verdict is Verdict.OK]
    status = Status.SURVIVES if fix_lanes and ok_lanes else Status.DEAD
    fix_names = ", ".join(sorted(lane.state for lane in fix_lanes))
    rio = next(lane for lane in lanes if lane.state == "RJ")
    evidence = (
        f"{len(ok_lanes)} lanes are already calibrated (OK) while {len(fix_lanes)} lanes "
        f"({fix_names}) are unpredictable rather than slow (FIX). Rio de Janeiro — the #2 "
        f"market by order count, next door to São Paulo — has a median delivery of "
        f"{rio.median_days:.0f} days but a p95 of {rio.p95_days:.0f} days. Distance cannot "
        f"explain Rio: it isn't far, it's unpredictable, and the current estimator is blind "
        f"to that."
    )
    return Hypothesis(
        name="variance_blindness",
        claim="The promise is adjusted for distance, but not for variance",
        status=status,
        evidence=evidence,
    )


def run_all(cassette: Cassette) -> list[Hypothesis]:
    return [
        check_churn(cassette),
        check_bad_sellers(cassette),
        check_review_damage(cassette),
        check_variance_blindness(cassette),
    ]
