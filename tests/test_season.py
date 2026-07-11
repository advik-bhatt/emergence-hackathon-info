import pytest
from promise_engine.analysis.season import MAX_FACTOR, MIN_FACTOR, SeasonModel
from promise_engine.craft.cassette import Cassette


@pytest.fixture(scope="module")
def season():
    return SeasonModel.from_cassette(Cassette("fixtures"))


def test_november_is_black_friday_and_runs_hot(season):
    """Black Friday: volume +63%, late rate tripled. November must come out > 1.0."""
    assert season.factor(11) > 1.0


@pytest.mark.parametrize("month", range(1, 13))
def test_every_month_is_clamped(month, season):
    assert MIN_FACTOR <= season.factor(month) <= MAX_FACTOR


def test_a_month_with_no_data_is_neutral(season):
    assert season.factor(13) == 1.0
