import pytest
from promise_engine.agent.narrative import HallucinatedNumber, check_numbers, extract_numbers


def test_extract_numbers_handles_integers_and_decimals():
    assert extract_numbers("RJ has p95 38.02 across 41 sellers") == {38.02, 41.0}


def test_extract_numbers_strips_thousands_separators():
    assert extract_numbers("Rio shipped 12,350 orders") == {12350.0}


def test_check_numbers_passes_when_every_number_was_computed():
    check_numbers(
        "Rio's p95 is 38 days across 12,350 orders",
        allowed={38.0, 12350.0},
    )


def test_check_numbers_raises_on_an_invented_delivery_date():
    with pytest.raises(HallucinatedNumber, match="41"):
        check_numbers(
            "Given the tail, we recommend promising 41 days for Rio.",
            allowed={38.0, 27.0, 12.0},
        )


def test_hallucinated_error_lists_what_was_computed():
    with pytest.raises(HallucinatedNumber, match=r"38.0|38\b"):
        check_numbers("we recommend promising 41 days", allowed={38.0, 12.0})


def test_small_prose_integers_are_allowed_without_being_computed():
    check_numbers(
        "There are two options here: about 1 in 7 orders run late, and 95% arrive on-time.",
        allowed=set(),
    )


def test_rounding_within_tolerance_is_accepted():
    # We computed 38.02; the model saying "38" should not be treated as invented.
    check_numbers("we computed a p95 of 38 days", allowed={38.02})


def test_rounding_outside_tolerance_still_raises():
    with pytest.raises(HallucinatedNumber):
        check_numbers("we computed a p95 of 39 days", allowed={38.02})


def test_percentages_are_checked_against_allowed():
    check_numbers("the late rate is 13.5%", allowed={13.47})
    with pytest.raises(HallucinatedNumber):
        check_numbers("the late rate is 25.0%", allowed={13.47})
