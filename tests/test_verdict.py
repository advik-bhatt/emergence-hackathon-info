import pytest
from promise_engine.analysis.verdict import Verdict, decide

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
