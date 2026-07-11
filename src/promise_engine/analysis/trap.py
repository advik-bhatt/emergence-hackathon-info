"""The trap: prove padding wins on the only metric this dataset can see, then refuse it.

`fixtures/review_damage.json` shows Early (4.29 avg review, 6.6% 1-star) beating On Time (4.03,
8.5%), and every later bucket (1-3 late, 4-7 late, ...) is worse still. Nothing in this dataset
penalizes a *longer* promise — the curve only goes one direction. So if you optimize the only
outcome Olist's data can measure, the answer is: pad the promise without limit. Every order
lands "early" relative to an ever-later estimate, reviews saturate at the Early bucket's score,
and the late rate hits zero.

That is a real result of the data, honestly computed — and this module computes it. It is also
the wrong answer, because the cost of an unbounded promise (a customer who sees "delivery in two
months" and never orders) does not appear anywhere in Olist's tables: there is no clickstream, no
session data, no cart events. The cost is not merely unmeasured, it is structurally
unmeasurable here. `why_we_refuse()` is the engine's refusal to chase a gradient it cannot see
the bottom of, and its fallback to a criterion — distance vs. variance — that does not need the
missing data at all.

CRITICAL: nothing here claims padding hurts conversion or revenue. The claim is the opposite:
that cost is unmeasurable in this dataset, which is exactly why the metric cannot be optimized
and the engine falls back to structural reasoning instead.
"""

from __future__ import annotations

from dataclasses import dataclass

from promise_engine.craft.cassette import Cassette

# Bucket name (lowercased, matched by substring so re-records with slightly different wording
# still resolve) -> representative lateness in days. Early is already early (no lateness to
# migrate away from); On Time is exactly on time; the late buckets use their midpoint, with
# "More Than 15 Days Late" given a conservative floor of 20 rather than an estimate of the true
# (higher) mean — understating how bad the tail is, which only strengthens the conclusion that
# padding helps.
_BUCKET_LATENESS: list[tuple[str, float]] = [
    ("early", -1.0),
    ("on time", 0.0),
    ("1-3", 2.0),
    ("4-7", 5.5),
    ("8-15", 11.5),
    ("more than 15", 20.0),
]


@dataclass(frozen=True)
class _Bucket:
    name: str
    lateness_days: float
    orders: int
    avg_review: float
    one_star_rate: float  # fraction, e.g. 0.066


@dataclass(frozen=True)
class CurvePoint:
    extra_days: int  # D: days added to every promise
    avg_review: float
    one_star_rate: float  # fraction, e.g. 0.066
    late_rate: float  # fraction of orders still late at this promise


@dataclass(frozen=True)
class NaiveOptimum:
    is_bounded: bool  # False
    saturation_days: int  # D beyond which the curve is flat
    best_avg_review: float  # ~4.29
    best_one_star_rate: float  # ~0.066
    baseline_avg_review: float
    baseline_one_star_rate: float
    verdict: str  # the punchline
    caveat: str  # the honest approximation note


def _match_lateness(bucket_name: str) -> float:
    name = bucket_name.strip().lower()
    for needle, lateness in _BUCKET_LATENESS:
        if needle in name:
            return lateness
    raise ValueError(
        f"Could not match delivery bucket {bucket_name!r} to a known lateness. "
        f"Extend _BUCKET_LATENESS in promise_engine/analysis/trap.py."
    )


def _load_buckets(cassette: Cassette) -> list[_Bucket]:
    rows = cassette.replay("review_damage").as_dicts()
    buckets = []
    for row in rows:
        name = str(row["delivery_bucket"])
        buckets.append(
            _Bucket(
                name=name,
                lateness_days=_match_lateness(name),
                orders=int(row["order_count"]),
                avg_review=float(row["avg_review_score"]),
                one_star_rate=float(row["pct_1_star_reviews"]) / 100.0,
            )
        )
    return buckets


def review_curve(cassette: Cassette, max_extra_days: int = 30) -> list[CurvePoint]:
    """Expected avg review, 1-star rate, and late rate if every promise were extended by D
    days, for D in 0..max_extra_days.

    Extending every promise by D days migrates an order OUT of a late bucket once
    D >= bucket_lateness: an order that used to arrive "4-7 days late" against the old,
    shorter promise now lands within the new, longer one. Migrated orders adopt the Early
    bucket's avg_review and 1-star rate — the best outcome this dataset ever records. Orders
    in buckets that haven't been reached yet (D < bucket_lateness) keep their own bucket's
    numbers. The order-weighted average is recomputed at each D.
    """
    buckets = _load_buckets(cassette)
    early = next(b for b in buckets if b.lateness_days < 0)
    total_orders = sum(b.orders for b in buckets)

    points = []
    for extra_days in range(0, max_extra_days + 1):
        review_sum = 0.0
        one_star_sum = 0.0
        late_orders = 0
        for bucket in buckets:
            migrated = extra_days >= bucket.lateness_days
            if migrated:
                review_sum += bucket.orders * early.avg_review
                one_star_sum += bucket.orders * early.one_star_rate
            else:
                review_sum += bucket.orders * bucket.avg_review
                one_star_sum += bucket.orders * bucket.one_star_rate
                if bucket.lateness_days > 0:
                    late_orders += bucket.orders

        points.append(
            CurvePoint(
                extra_days=extra_days,
                avg_review=review_sum / total_orders,
                one_star_rate=one_star_sum / total_orders,
                late_rate=late_orders / total_orders,
            )
        )
    return points


def naive_review_optimum(cassette: Cassette, max_extra_days: int = 30) -> NaiveOptimum:
    """The promise extension that maximizes measured reviews. It is unbounded.

    Every bucket's lateness is finite, so this curve does saturate at some finite D within
    max_extra_days — but that saturation point is an artifact of the bucket boundaries the
    fixture happens to define (the last one tops out at a 20-day floor), not a real stopping
    rule the data provides. Nothing in the curve ever turns over: no amount of extra promise
    ever makes reviews worse. Extend the buckets and the "optimal" D extends right along with
    them. That is what "unbounded" means here — not that the number never converges, but that
    the data supplies no principled place to stop before it does.
    """
    curve = review_curve(cassette, max_extra_days=max_extra_days)
    buckets = _load_buckets(cassette)
    baseline = curve[0]
    best = curve[-1]

    saturation_days = next(
        (point.extra_days for point in curve if point.avg_review >= best.avg_review - 1e-9),
        curve[-1].extra_days,
    )

    verdict = (
        "UNBOUNDED. Every additional day of promise is free: extending the delivery promise "
        "by D days never once makes the measured outcome worse. Reviews rise monotonically to "
        f"{best.avg_review:.2f}/5 and the late rate falls to zero, and the data never once "
        "says stop. Optimizing the only outcome this dataset measures, the recommended promise "
        "is +infinity: pad it forever, the curve keeps climbing no matter how far out you push "
        "it, because no bucket in this fixture ever penalizes being early. That is the trap."
    )
    caveat = (
        "This uses bucket MIDPOINTS (Early=-1, On Time=0, 1-3 late=2, 4-7 late=5.5, "
        "8-15 late=11.5, 15+ late=20 as a conservative floor), not exact per-order lateness — "
        "we do not have that. But the conclusion does not depend on that precision: no bucket "
        "in review_damage.json penalizes an order for arriving early, at any distance. The "
        "curve cannot turn over regardless of where the exact midpoints fall. That is the "
        "point — the shape of the trap, not the precision of the approximation, is what makes "
        "the optimum unbounded."
    )

    return NaiveOptimum(
        is_bounded=False,
        saturation_days=saturation_days,
        best_avg_review=best.avg_review,
        best_one_star_rate=best.one_star_rate,
        baseline_avg_review=baseline.avg_review,
        baseline_one_star_rate=baseline.one_star_rate,
        verdict=verdict,
        caveat=caveat,
    )


def why_we_refuse() -> str:
    """The refusal. This is the engine's defining act: it can prove padding wins on the only
    metric it can see, and it declines to recommend it — because the cost of that padding is
    not merely unmeasured in Olist's data, it is structurally unmeasurable, and an engine that
    follows a gradient it cannot see the bottom of is not reasoning, it is guessing with
    confidence.
    """
    return (
        "We decline this optimum. The cost of a long promise is a customer who sees "
        "\"delivery in 2 months\" at checkout and never orders at all — and Olist has no "
        "clickstream: no sessions, no page views, no cart events, nothing upstream of the "
        "order itself. That cost is not merely unmeasured, it is structurally unmeasurable in "
        "this dataset. So we do not follow the gradient, no matter how cleanly it points "
        "toward +infinity. We fall back to a criterion that does not need the missing data: is "
        "a lane's gap DISTANCE (median — irreducible, so padding is honest) or VARIANCE "
        "(p95 minus median — recoverable, so the lane should be fixed instead)? That question "
        "is answerable entirely from delivery data we already have, and it never asks the "
        "review curve to tell us where to stop."
    )
