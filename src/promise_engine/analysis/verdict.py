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
