import pytest
from promise_engine.analysis.lanes import load_lanes, rank_by_orders_at_risk
from promise_engine.analysis.verdict import Verdict
from promise_engine.craft.cassette import Cassette


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
