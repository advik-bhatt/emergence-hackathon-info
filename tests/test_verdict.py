import pytest
from promise_engine.analysis.verdict import Verdict, decide, flip_distance_days

# (state, promised, median, p95, expected) — verified against live Olist data
GROUND_TRUTH = [
    ("SP", 19.8, 7.0, 20.0, Verdict.OK),
    ("MG", 25.2, 10.0, 24.4, Verdict.OK),
    ("PR", 25.3, 10.0, 25.0, Verdict.OK),
    ("DF", 24.9, 11.0, 26.0, Verdict.OK),   # gap +1.1, inside tolerance
    ("MT", 32.4, 16.0, 34.0, Verdict.PAD),
    ("BA", 30.1, 17.0, 37.0, Verdict.PAD),
    ("PA", 37.8, 21.0, 46.8, Verdict.PAD),  # genuinely far — padding is honest
    ("MA", 31.1, 19.0, 41.2, Verdict.PAD),
    ("RS", 29.2, 13.0, 33.0, Verdict.FIX),  # var share 0.606 — the lane humans missed
    ("RJ", 27.0, 12.0, 38.0, Verdict.FIX),
    ("CE", 32.0, 18.0, 45.0, Verdict.FIX),
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


def test_zero_p95_does_not_divide_by_zero():
    assert decide(promised_days=1.0, median_days=0.0, p95_days=0.0) == Verdict.OK


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
