"""Lane.__post_init__ validation — the guard that turns a silent mis-resolved column
(e.g. a re-record swapping PROMISED_DAYS to hold the recommended promise instead of the
current one) into a loud failure instead of a quietly wrong verdict."""

import math

import pytest
from promise_engine.analysis.lanes import load_lanes
from promise_engine.craft.cassette import Cassette
from promise_engine.models import Lane

VALID = dict(state="XX", orders=1000, promised_days=27.0, median_days=12.0,
             p95_days=38.0, late_rate=0.1347)


def _lane(**overrides):
    return Lane(**{**VALID, **overrides})


def test_valid_lane_constructs_fine():
    _lane()


def test_orders_must_be_positive():
    with pytest.raises(ValueError, match="orders"):
        _lane(orders=-5)


def test_orders_zero_is_rejected():
    with pytest.raises(ValueError, match="orders"):
        _lane(orders=0)


def test_p95_below_median_is_rejected():
    """A p95 cannot fall below its own median — this is the garbage case from the review:
    orders=-5, median=40, p95=12."""
    with pytest.raises(ValueError, match="p95"):
        _lane(median_days=40.0, p95_days=12.0)


def test_promised_days_must_be_positive():
    with pytest.raises(ValueError, match="promised_days"):
        _lane(promised_days=0.0)


def test_promised_days_negative_is_rejected():
    with pytest.raises(ValueError, match="promised_days"):
        _lane(promised_days=-1.0)


def test_late_rate_below_zero_is_rejected():
    with pytest.raises(ValueError, match="late_rate"):
        _lane(late_rate=-300.0)


def test_late_rate_above_one_is_rejected():
    with pytest.raises(ValueError, match="late_rate"):
        _lane(late_rate=1.5)


@pytest.mark.parametrize("field", ["promised_days", "median_days", "p95_days", "late_rate"])
def test_nan_field_is_rejected(field):
    """decide() returns a confident PAD for NaN inputs because every NaN comparison is
    False, so both guards fall through silently. The invariant must kill this at
    construction time instead."""
    with pytest.raises(ValueError, match=field):
        _lane(**{field: math.nan})


def test_infinite_field_is_rejected():
    with pytest.raises(ValueError, match="p95_days"):
        _lane(p95_days=math.inf)


def test_all_17_real_lanes_load_without_error():
    lanes = load_lanes(Cassette("fixtures").replay("lanes"))
    assert len(lanes) == 17
