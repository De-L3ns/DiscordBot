from datetime import date

import pytest

from kletserbot.domain.birthdays.birthday import Birthday
from kletserbot.domain.birthdays.birthday_calculator import (
    calculate_age_on_date,
    is_birthday_on_date,
)


def test_matching_birthday_returns_current_age() -> None:
    birthday = Birthday("Laurens", date(1993, 7, 21))

    assert calculate_age_on_date(birthday, date(2026, 7, 21)) == 33


def test_age_before_birthday_excludes_current_year() -> None:
    birthday = Birthday("Laurens", date(1993, 7, 21))

    assert calculate_age_on_date(birthday, date(2026, 7, 20)) == 32


def test_leap_day_birthday_matches_february_28_in_non_leap_year() -> None:
    birthday = Birthday("Leap", date(2000, 2, 29))

    assert is_birthday_on_date(birthday, date(2025, 2, 28)) is True
    assert calculate_age_on_date(birthday, date(2025, 2, 28)) == 25


def test_empty_person_name_is_rejected() -> None:
    with pytest.raises(ValueError, match="person_name"):
        Birthday(" ", date(2000, 1, 1))
