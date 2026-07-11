import pytest
from promise_engine.analysis.hypotheses import Status, run_all
from promise_engine.craft.cassette import Cassette


@pytest.fixture(scope="module")
def hypotheses():
    return {h.name: h for h in run_all(Cassette("fixtures"))}


def test_churn_is_dead(hypotheses):
    """The hypothesis the hackathon guide itself suggested. It is false."""
    assert hypotheses["churn"].status is Status.DEAD


def test_bad_sellers_is_dead(hypotheses):
    assert hypotheses["bad_sellers"].status is Status.DEAD


def test_review_damage_survives(hypotheses):
    assert hypotheses["review_damage"].status is Status.SURVIVES


def test_variance_blindness_survives(hypotheses):
    assert hypotheses["variance_blindness"].status is Status.SURVIVES


@pytest.mark.parametrize(
    "name", ["churn", "bad_sellers", "review_damage", "variance_blindness"]
)
def test_every_hypothesis_has_evidence(name, hypotheses):
    assert hypotheses[name].evidence.strip() != ""
    assert hypotheses[name].claim.strip() != ""


def test_churn_evidence_cites_the_overall_rate_and_the_spread(hypotheses):
    evidence = hypotheses["churn"].evidence
    assert "3.12" in evidence  # overall repeat rate
    assert "2.81" in evidence  # min cohort (2-star)
    assert "3.22" in evidence  # max cohort (5-star)


def test_bad_sellers_evidence_cites_the_volume_artifact(hypotheses):
    evidence = hypotheses["bad_sellers"].evidence
    assert "7.87" in evidence  # baseline late rate
    assert "9.39" in evidence  # top-30 combined late rate
    assert "32.1" in evidence  # highest single-seller late rate


def test_review_damage_evidence_cites_the_score_collapse(hypotheses):
    evidence = hypotheses["review_damage"].evidence
    assert "4.29" in evidence
    assert "1.68" in evidence


def test_variance_blindness_evidence_names_rio(hypotheses):
    evidence = hypotheses["variance_blindness"].evidence
    assert "Rio" in evidence
    assert "12" in evidence
    assert "38" in evidence
