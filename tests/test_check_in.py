from src.ui.check_in_page import CheckInPage
from src.ui.check_in_page import classify_baseline

# Simple helper used only to return the translation key
class TestCheckIn:
    @staticmethod
    def t(key):
        return key


page = TestCheckIn()


# Test case 1: Check that the first high wellbeing score uses the high result
def test_first_high_result():
    phrase, explanation, image = (
        CheckInPage.result_text(
            page,
            67,
            None
        )
    )

    assert phrase == "first_high_phrase"
    assert explanation == "first_high_text"
    assert image == "wellbeing_high.png"


# Test case 2: Check that the first middle wellbeing score uses the middle result
def test_first_middle_result():
    phrase, explanation, image = (
        CheckInPage.result_text(
            page,
            34,
            None
        )
    )

    assert phrase == "first_mid_phrase"
    assert explanation == "first_mid_text"
    assert image == "wellbeing_mid.png"


# Test case 3: Check that the first low wellbeing score uses the low result
def test_first_low_result():
    phrase, explanation, image = (
        CheckInPage.result_text(
            page,
            33,
            None
        )
    )

    assert phrase == "first_low_phrase"
    assert explanation == "first_low_text"
    assert image == "wellbeing_low.png"


# Test case 4: Check that an increase of 5 points is treated as improved
def test_improved_result():
    phrase, explanation, image = (
        CheckInPage.result_text(
            page,
            65,
            60
        )
    )

    assert phrase == "improved_phrase"
    assert explanation == "improved_text"
    assert image == "wellbeing_high.png"


# Test case 5: Check that a decrease of 5 points is treated as lower
def test_lower_result():
    phrase, explanation, image = (
        CheckInPage.result_text(
            page,
            55,
            60
        )
    )

    assert phrase == "lower_phrase"
    assert explanation == "lower_text"
    assert image == "wellbeing_low.png"


# Test case 6: Check that a small increase is treated as steady
def test_small_increase_is_steady():
    phrase, explanation, image = (
        CheckInPage.result_text(
            page,
            64,
            60
        )
    )

    assert phrase == "steady_phrase"
    assert explanation == "steady_text"
    assert image == "wellbeing_mid.png"


# Test case 7: Check that a small decrease is treated as steady
def test_small_decrease_is_steady():
    phrase, explanation, image = (
        CheckInPage.result_text(
            page,
            56,
            60
        )
    )

    assert phrase == "steady_phrase"
    assert explanation == "steady_text"
    assert image == "wellbeing_mid.png"


# Test case 8: Check that the same score is treated as steady
def test_same_score_is_steady():
    phrase, explanation, image = (
        CheckInPage.result_text(
            page,
            60,
            60
        )
    )

    assert phrase == "steady_phrase"
    assert explanation == "steady_text"
    assert image == "wellbeing_mid.png"

# Test: not enough history returns None
def test_baseline_not_enough_history():
    scores = [50, 55, 60]  # fewer than 7
    assert classify_baseline(70, scores) is None


# Test: a score clearly above the recent range
def test_baseline_above_range():
    scores = [50, 52, 48, 51, 49, 50, 50]  # mean 50, small SD
    assert classify_baseline(80, scores) == "baseline_above"


# Test: a score clearly below the recent range
def test_baseline_below_range():
    scores = [50, 52, 48, 51, 49, 50, 50]
    assert classify_baseline(20, scores) == "baseline_below"


# Test: a score within the recent range
def test_baseline_within_range():
    scores = [50, 52, 48, 51, 49, 50, 50]
    assert classify_baseline(50, scores) == "baseline_within"


def test_baseline_zero_sd_above():
    scores = [50, 50, 50, 50, 50, 50, 50]
    assert classify_baseline(60, scores) == "baseline_above"


def test_baseline_zero_sd_same():
    scores = [50, 50, 50, 50, 50, 50, 50]
    assert classify_baseline(50, scores) == "baseline_within"