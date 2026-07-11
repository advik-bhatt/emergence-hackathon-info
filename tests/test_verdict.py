import pytest
from promise_engine.analysis.verdict import Verdict, decide, flip_distance_days, tail_fraction

# (state, promised, median, p95, expected) — all 17 lanes with >= 500 orders in the Olist
# fixture (fixtures/lanes.json). Expected verdict is reasoned out from the rule itself, not
# copied from whatever the code currently returns:
#
#   gap = p95 - promised; if gap <= 1.5 -> OK
#   tail_fraction = (p95 - median) / p95; if tail_fraction >= 0.60 AND (p95 - median) >= 5.0
#       -> FIX
#   else -> PAD
#
# gap and tail_fraction are noted per lane so the expected column can be checked by eye.
GROUND_TRUTH = [
    # --- OK: gap <= 1.5 --------------------------------------------------------------
    ("MG", 25.2, 10.0, 24.4, Verdict.OK),   # gap -0.8
    ("PR", 25.3, 10.0, 25.0, Verdict.OK),   # gap -0.3
    ("SP", 19.8, 7.0, 20.0, Verdict.OK),    # gap +0.2
    ("DF", 24.9, 11.0, 26.0, Verdict.OK),   # gap +1.1
    ("GO", 27.7, 14.0, 29.0, Verdict.OK),   # gap +1.3
    # --- FIX: gap > 1.5 and tail_fraction >= 0.60 (and tail >= 5.0) -------------------
    ("RS", 29.2, 13.0, 33.0, Verdict.FIX),  # gap +3.8, tail_fraction 20/33 = 0.606
    ("RJ", 27.0, 12.0, 38.0, Verdict.FIX),  # gap +11.0, tail_fraction 26/38 = 0.684
    ("CE", 32.0, 18.0, 45.0, Verdict.FIX),  # gap +13.0, tail_fraction 27/45 = 0.600 exactly
    # --- PAD: gap > 1.5 but tail_fraction < 0.60 --------------------------------------
    ("MT", 32.4, 16.0, 34.0, Verdict.PAD),  # gap +1.6, tail_fraction 18/34 = 0.529
    ("MS", 26.6, 14.0, 31.0, Verdict.PAD),  # gap +4.4, tail_fraction 17/31 = 0.548
    ("SC", 26.4, 13.0, 31.0, Verdict.PAD),  # gap +4.6, tail_fraction 18/31 = 0.581
    ("ES", 26.2, 14.0, 31.0, Verdict.PAD),  # gap +4.8, tail_fraction 17/31 = 0.548
    ("PB", 33.6, 18.0, 40.2, Verdict.PAD),  # gap +6.6, tail_fraction 22.2/40.2 = 0.552
    ("BA", 30.1, 17.0, 37.0, Verdict.PAD),  # gap +6.9, tail_fraction 20/37 = 0.541
    ("PE", 31.7, 16.0, 39.4, Verdict.PAD),  # gap +7.7, tail_fraction 23.4/39.4 = 0.594
    ("PA", 37.8, 21.0, 46.8, Verdict.PAD),  # gap +9.0, tail_fraction 25.8/46.8 = 0.551
    ("MA", 31.1, 19.0, 41.2, Verdict.PAD),  # gap +10.1, tail_fraction 22.2/41.2 = 0.539
]


@pytest.mark.parametrize("state,promised,median,p95,expected", GROUND_TRUTH)
def test_verdict_matches_ground_truth(state, promised, median, p95, expected):
    assert decide(promised_days=promised, median_days=median, p95_days=p95) == expected


def test_calibrated_lane_is_ok_even_with_a_fat_tail():
    """A lane can be volatile and still need no action if the promise already covers it.
    We must not cry wolf on lanes that are already calibrated."""
    assert decide(promised_days=40.0, median_days=5.0, p95_days=39.0) == Verdict.OK


def test_slow_but_predictable_lane_pads():
    """High median, thin tail: it really is far away. Padding is honest."""
    assert decide(promised_days=20.0, median_days=30.0, p95_days=35.0) == Verdict.PAD


def test_fast_but_unpredictable_lane_fixes():
    """Low median, fat tail: it isn't slow, it's unreliable. Don't pad — fix it."""
    assert decide(promised_days=20.0, median_days=5.0, p95_days=40.0) == Verdict.FIX


def test_tail_fraction_zero_p95_does_not_divide_by_zero():
    """decide(promised_days=1.0, median_days=0.0, p95_days=0.0) never actually reaches the
    division: gap = 0 - 1 = -1 <= 1.5, so it short-circuits to OK before tail_fraction is
    even called. Exercise the zero-p95 guard directly instead."""
    assert tail_fraction(0.0, 0.0) == 0.0


# --- FIX 6: boundary tests --------------------------------------------------------------

def test_gap_exactly_at_tolerance_is_ok():
    """gap == OK_TOLERANCE_DAYS (1.5) must be OK: the comparison is <=."""
    assert decide(promised_days=10.0, median_days=5.0, p95_days=11.5) == Verdict.OK


def test_gap_just_over_tolerance_is_not_ok():
    """gap == 1.51, one hundredth of a day over tolerance, must not be OK."""
    assert decide(promised_days=10.0, median_days=5.0, p95_days=11.51) != Verdict.OK


def test_tail_fraction_exactly_at_threshold_is_fix():
    """tail_fraction == VARIANCE_DOMINANT_SHARE (0.60) exactly must be FIX: the comparison
    is >=. This is CE's literal value (27/45 == 0.60) — not a synthetic edge case."""
    assert tail_fraction(18.0, 45.0) == pytest.approx(0.60)
    assert decide(promised_days=32.0, median_days=18.0, p95_days=45.0) == Verdict.FIX


# --- FIX 4: robustness reporting -------------------------------------------------------

def test_rio_flip_distance_is_about_8_point_1_days():
    """Rio's tail would have to shrink 8.1 days before the verdict flips to PAD — the
    thesis lane is not on a knife edge."""
    distance = flip_distance_days(promised_days=27.0, median_days=12.0, p95_days=38.0)
    assert distance == pytest.approx(8.1, abs=0.05)


def test_ceara_flip_distance_is_about_0_point_1_days():
    """Ceara sits exactly on the tail_fraction cut (27/45 == 0.60): it is on a knife edge."""
    distance = flip_distance_days(promised_days=32.0, median_days=18.0, p95_days=45.0)
    assert distance == pytest.approx(0.1, abs=0.05)


# --- FIX 5(a): absolute floor on FIX -----------------------------------------------------

def test_same_day_lane_with_trivial_tail_does_not_get_fix():
    """Because the discriminator is a pure ratio, a same-day lane with a 1.8-day tail
    (promised=0.4, median=0.2, p95=2.0) clears the 0.60 tail_fraction and would otherwise be
    dispatched to ops as 'attack the tail' at a scale where that is nonsense. Below the
    absolute floor, decide must fall through to PAD instead of FIX."""
    assert decide(promised_days=0.4, median_days=0.2, p95_days=2.0) == Verdict.PAD


@pytest.mark.parametrize("state,promised,median,p95", [
    ("RJ", 27.0, 12.0, 38.0),
    ("RS", 29.2, 13.0, 33.0),
    ("CE", 32.0, 18.0, 45.0),
])
def test_real_fix_lanes_are_unaffected_by_the_absolute_floor(state, promised, median, p95):
    """All three real FIX lanes have tails of 26.0, 20.0 and 27.0 days — comfortably above
    the 5.0-day floor — so introducing it must not change their verdict."""
    assert decide(promised_days=promised, median_days=median, p95_days=p95) == Verdict.FIX
