"""The pad-vs-fix decision.

The gap between what a lane needs and what it promises decomposes into two parts:

    distance component = median          — irreducible. The lane really is far.
    variance component = p95 - median    — recoverable. This is the tail.

If the variance component dominates, the lane is unpredictable rather than slow, and padding
the promise would be the wrong answer: you'd keep your word by telling Rio customers to wait
38 days for a parcel that usually arrives in 12.

If the median itself is what's large, the lane is genuinely far away and padding is honest.
"""

from enum import Enum


class Verdict(str, Enum):
    OK = "OK"      # already calibrated — no action
    PAD = "PAD"    # genuinely slow — lengthen the promise
    FIX = "FIX"    # unpredictable, not slow — attack the tail


# A lane whose promise is within this many days of what it needs is already calibrated.
# SP (+0.2), MG (-0.8), PR (-0.3) and DF (+1.1) sit inside it: the estimator is not stupid,
# and an engine that flagged them would be crying wolf.
OK_TOLERANCE_DAYS = 1.5

# Share of the required promise that is tail rather than distance. Above this, the lane's
# problem is volatility. Calibrated against Olist: RJ 0.684, RS 0.606 and CE 0.600 clear it;
# BA 0.541, MA 0.539 and PA 0.551 do not.
#
# This is a chosen operating point, not a natural boundary in the data: sorted by score,
# the lowest FIX (CE, 0.600) and the highest PAD (PE, 0.594) are 0.006 apart, and CE sits
# EXACTLY on the cut. Five of the seventeen lanes are within +/-0.6 days of flipping verdict
# if the threshold moved. RJ — the thesis lane — is robust to it: its p95 would have to fall
# 8.1 days before it would stop being FIX. Several smaller lanes are not nearly so robust,
# which is why decide is not the whole story — Lane also reports flip_distance and
# is_borderline, so fragility near this boundary is visible rather than hidden.
VARIANCE_DOMINANT_SHARE = 0.60


def tail_fraction(median_days: float, p95_days: float) -> float:
    """Fraction of the required promise (p95) that is TAIL rather than DISTANCE:

        tail_fraction = (p95 - median) / p95 = 1 - median / p95

    This is only meaningful conditional on the lane actually having a gap — for an
    already-calibrated lane (promise ~= p95) it says nothing about whether the lane is
    "volatile", because it is monotonically decreasing in the median: fast, well-calibrated
    lanes trivially score high on it too. (São Paulo scores 0.650 on this metric alone —
    higher than two of the three real FIX lanes — and is only saved from being flagged by
    the OK short-circuit in decide(). Do not rank lanes by this property expecting it to
    mean "volatility" in general; it only means that inside decide(), after the gap check.)
    """
    if p95_days <= 0:
        return 0.0
    return (p95_days - median_days) / p95_days


def decide(*, promised_days: float, median_days: float, p95_days: float) -> Verdict:
    gap = p95_days - promised_days
    if gap <= OK_TOLERANCE_DAYS:
        return Verdict.OK
    if tail_fraction(median_days, p95_days) >= VARIANCE_DOMINANT_SHARE:
        return Verdict.FIX
    return Verdict.PAD


# Step size (days) used to search for the nearest verdict-flip point, matching the
# precision the fixtures are rounded to.
_FLIP_SEARCH_STEP_DAYS = 0.1
# No real lane needs anywhere near this much movement; this just keeps the search finite.
_FLIP_SEARCH_HORIZON_DAYS = 10_000.0


def flip_distance_days(*, promised_days: float, median_days: float, p95_days: float) -> float:
    """How many days p95 would have to move for this lane's verdict to change.

    Rio's is 8.1 — the thesis lane is not on a knife edge. Ceara's is 0.1 — it is.
    An engine that reports FIX for both without saying which is which is lying by omission.

    Searches outward from the current p95 in both directions, in
    _FLIP_SEARCH_STEP_DAYS increments, for the nearest point at which decide() returns a
    different verdict than it does today, holding promised_days and median_days fixed.
    """
    current = decide(promised_days=promised_days, median_days=median_days, p95_days=p95_days)
    distance = _FLIP_SEARCH_STEP_DAYS
    while distance <= _FLIP_SEARCH_HORIZON_DAYS:
        for direction in (1.0, -1.0):
            candidate_p95 = p95_days + direction * distance
            if candidate_p95 < 0:
                continue
            candidate = decide(
                promised_days=promised_days, median_days=median_days, p95_days=candidate_p95,
            )
            if candidate != current:
                return round(distance, 1)
        distance = round(distance + _FLIP_SEARCH_STEP_DAYS, 1)
    return round(_FLIP_SEARCH_HORIZON_DAYS, 1)
