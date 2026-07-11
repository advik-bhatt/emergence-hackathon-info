import pytest
from promise_engine.analysis.lanes import load_lanes, rank_by_orders_at_risk
from promise_engine.analysis.verdict import Verdict
from promise_engine.craft.cassette import Cassette, QueryResult

# A minimal set of columns covering every other concept lanes.py needs, so tests below
# can vary just the late-rate column without tripping unrelated KeyErrors.
_BASE_COLUMNS = [
    "CUSTOMER_STATE", "ORDER_COUNT", "AVG_PROMISED_DAYS", "MEDIAN_ACTUAL_DAYS",
    "P95_ACTUAL_DAYS",
]
_BASE_ROW = ["XX", 1000, 10.0, 5.0, 12.0]


def _qr(extra_columns, extra_values):
    return QueryResult(
        slug="synthetic", nl_question="q", sql="s",
        columns=[*_BASE_COLUMNS, *extra_columns],
        rows=[[*_BASE_ROW, *extra_values]],
    )


@pytest.fixture(scope="module")
def lanes():
    return {l.state: l for l in load_lanes(Cassette("fixtures").replay("lanes"))}


def test_rio_is_the_thesis(lanes):
    rj = lanes["RJ"]
    assert rj.orders == 12350
    assert rj.median_days == pytest.approx(12, abs=1)
    assert rj.p95_days == pytest.approx(38, abs=1.5)
    assert rj.recommended_promise == rj.p95_days
    assert rj.gap == pytest.approx(11, abs=1.5)
    assert rj.verdict is Verdict.FIX


def test_rio_is_unpredictable_not_slow(lanes):
    """The whole thesis in one assertion: Rio's median beats several PAD lanes,
    but its tail is the worst in the country."""
    assert lanes["RJ"].median_days < lanes["BA"].median_days
    assert lanes["RJ"].variance_share > lanes["BA"].variance_share


def test_sao_paulo_is_already_calibrated(lanes):
    assert lanes["SP"].gap == pytest.approx(0.2, abs=1.0)
    assert lanes["SP"].verdict is Verdict.OK


@pytest.mark.parametrize("state", ["SP", "MG", "PR"])
def test_we_do_not_cry_wolf_on_calibrated_lanes(state, lanes):
    assert lanes[state].verdict is Verdict.OK


def test_late_rate_is_normalized_to_a_fraction(lanes):
    """CRAFT returns 13.47 (percent). We store 0.1347."""
    assert lanes["RJ"].late_rate == pytest.approx(0.1347, abs=0.001)


def test_orders_at_risk_ranks_rio_first(lanes):
    ranked = rank_by_orders_at_risk(lanes.values())
    assert ranked[0].state == "RJ", "Rio must top the ops queue: +11 days x 12,350 orders"
    assert ranked[0].orders_at_risk == pytest.approx(11 * 12350, rel=0.1)


def test_calibrated_lanes_carry_no_risk(lanes):
    """SP has a fractionally positive gap (+0.2) across 40,501 orders. If we multiplied
    those out it would score 8,100 and outrank Para — sending ops to fix a lane that is
    already fine. A lane we judged OK carries no risk by definition."""
    assert lanes["SP"].orders_at_risk == 0
    assert lanes["SP"].orders_at_risk < lanes["PA"].orders_at_risk


# --- FIX 1: unit inference must come from the column name, not the magnitude ---------

def test_late_rate_pct_suffix_is_treated_as_a_percent_even_when_small():
    """The bug: a genuine late rate of 0.85% must not be mistaken for a fraction of 0.85
    (85% late) just because 0.85 fails a `> 1` magnitude check. The column name says PCT,
    so it must always be divided by 100, regardless of magnitude."""
    lane = load_lanes(_qr(["LATE_RATE_PCT"], [0.85]))[0]
    assert lane.late_rate == pytest.approx(0.0085)


def test_late_rate_without_pct_suffix_is_already_a_fraction():
    lane = load_lanes(_qr(["LATE_RATE"], [0.0085]))[0]
    assert lane.late_rate == pytest.approx(0.0085)


def test_impossible_late_rate_pct_raises_value_error():
    """150% late is impossible; this must be a loud failure, not a silently stored 1.5."""
    with pytest.raises(ValueError):
        load_lanes(_qr(["LATE_RATE_PCT"], [150.0]))


def test_real_rj_fixture_still_loads_the_correct_late_rate(lanes):
    assert lanes["RJ"].late_rate == pytest.approx(0.1347, abs=0.0001)


# --- FIX 6: alias resolution is the whole stated purpose of lanes.py -------------------

def test_fallback_alias_resolves():
    """A concept whose column uses a non-primary alias must still resolve."""
    qr = QueryResult(
        slug="synthetic", nl_question="q", sql="s",
        columns=[
            "DELIVERY_STATE", "NUM_ORDERS", "AVERAGE_PROMISED_DAYS",
            "MEDIAN_DELIVERY_DAYS", "PERCENTILE_95_DAYS", "PCT_LATE",
        ],
        rows=[["ZZ", 1000, 10.0, 5.0, 12.0, 5.0]],
    )
    lane = load_lanes(qr)[0]
    assert lane.state == "ZZ"
    assert lane.orders == 1000
    assert lane.late_rate == pytest.approx(0.05)


def test_missing_concept_raises_keyerror_naming_the_concept():
    """If no alias for a concept is present, the error must name the missing concept and
    tell the caller what to edit — not raise a bare KeyError deep in dataclass construction."""
    qr = QueryResult(
        slug="synthetic", nl_question="q", sql="s",
        # p95_days concept is entirely absent
        columns=["CUSTOMER_STATE", "ORDER_COUNT", "AVG_PROMISED_DAYS",
                 "MEDIAN_ACTUAL_DAYS", "LATE_RATE_PCT"],
        rows=[["ZZ", 1000, 10.0, 5.0, 5.0]],
    )
    with pytest.raises(KeyError) as exc_info:
        load_lanes(qr)
    message = str(exc_info.value)
    assert "p95_days" in message
    assert "ALIASES" in message
