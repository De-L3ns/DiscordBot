import calendar
from datetime import date

from kletserbot.apps.general.domain.birthdays.birthday import Birthday


def is_birthday_on_date(birthday: Birthday, current_date: date) -> bool:
    observed_month, observed_day = _observed_birthday(
        birthday.birth_date,
        current_date.year,
    )
    return (current_date.month, current_date.day) == (
        observed_month,
        observed_day,
    )


def calculate_age_on_date(birthday: Birthday, current_date: date) -> int:
    observed_month, observed_day = _observed_birthday(
        birthday.birth_date,
        current_date.year,
    )
    has_not_had_birthday = (current_date.month, current_date.day) < (
        observed_month,
        observed_day,
    )
    return current_date.year - birthday.birth_date.year - int(has_not_had_birthday)


def _observed_birthday(birth_date: date, year: int) -> tuple[int, int]:
    if birth_date.month == 2 and birth_date.day == 29 and not calendar.isleap(year):
        return (2, 28)
    return (birth_date.month, birth_date.day)
