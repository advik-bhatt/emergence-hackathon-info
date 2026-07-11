import pytest
from promise_engine.analysis.promise import PromiseEngine
from promise_engine.analysis.verdict import Verdict
from promise_engine.craft.cassette import Cassette

# Real seller ids from fixtures/seller_handling.json.
MEDIAN_SELLER = "729f06993dac8e860d4f02d7088ca48a"  # p95_handling_days == 5.0 (national median)
BEST_SELLER = "b1a81260566c1bac3114a6d124413f27"  # lowest p95_handling_days (1.349)
WORST_SELLER = "54965bbe3e4f07ae045b90b0b8541f52"  # highest p95_handling_days (41.0)
UNKNOWN_SELLER = "does-not-exist-in-any-fixture"


@pytest.fixture(scope="module")
def engine():
    return PromiseEngine.from_cassette(Cassette("fixtures"))


def test_promise_decomposes_exactly_into_its_parts(engine):
    quote = engine.quote(seller_id=MEDIAN_SELLER, state="RJ")
    assert quote.days == quote.handling_days + quote.transit_days


def test_rio_quote_is_fix_and_transit_dominates(engine):
    quote = engine.quote(seller_id=MEDIAN_SELLER, state="RJ")
    assert quote.verdict is Verdict.FIX
    assert quote.transit_days > quote.handling_days


def test_decomposition_reconciles_with_lane_p95(engine):
    """A median-handling seller's quote must land within 2 days of RJ's own p95 (38):
    handling 5.0 + transit 34.0 = 39, vs the lane's end-to-end p95 of 38."""
    quote = engine.quote(seller_id=MEDIAN_SELLER, state="RJ")
    assert quote.days == pytest.approx(38, abs=2)


def test_unknown_seller_falls_back_to_national_median(engine):
    quote = engine.quote(seller_id=UNKNOWN_SELLER, state="RJ")
    assert quote.handling_is_fallback is True
    assert quote.handling_days > 0


def test_known_seller_is_not_a_fallback(engine):
    quote = engine.quote(seller_id=MEDIAN_SELLER, state="RJ")
    assert quote.handling_is_fallback is False


def test_seasonality_is_off_by_default(engine):
    quote = engine.quote(seller_id=MEDIAN_SELLER, state="RJ")
    assert quote.season_factor == 1.0
    assert quote.season_days == 0.0


def test_black_friday_lengthens_the_promise_when_opted_in(engine):
    base = engine.quote(seller_id=MEDIAN_SELLER, state="RJ")
    november = engine.quote(seller_id=MEDIAN_SELLER, state="RJ", month=11, seasonal=True)
    assert november.days > base.days
    assert november.season_days > 0


def test_seller_attribution_is_real(engine):
    """The worst-handling seller's quote must exceed the best-handling seller's quote by
    roughly the difference in their handling p95 — the lane component is held constant."""
    worst = engine.quote(seller_id=WORST_SELLER, state="RJ")
    best = engine.quote(seller_id=BEST_SELLER, state="RJ")
    handling_gap = worst.handling_days - best.handling_days
    assert (worst.days - best.days) == pytest.approx(handling_gap, abs=0.01)
    assert handling_gap > 30  # 41.0 vs 1.349


def test_unknown_state_raises_key_error(engine):
    with pytest.raises(KeyError):
        engine.quote(seller_id=engine.any_seller(), state="ZZ")
