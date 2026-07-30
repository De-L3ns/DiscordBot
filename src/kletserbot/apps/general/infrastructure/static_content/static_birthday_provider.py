from datetime import date

from kletserbot.apps.general.domain.birthdays.birthday import Birthday


class StaticBirthdayProvider:
    _BIRTHDAYS = (
        Birthday("Max", date(1991, 9, 16)),
        Birthday("Kobe", date(1992, 2, 20)),
        Birthday("Freek", date(1993, 3, 1)),
        Birthday("Joachim", date(1990, 6, 27)),
        Birthday("Leander", date(1990, 3, 2)),
        Birthday("Matthieu", date(1993, 3, 9)),
        Birthday("Fabian", date(1994, 6, 28)),
        Birthday("Laurens", date(1993, 7, 21)),
        Birthday("Jochen", date(1990, 9, 5)),
    )

    def retrieve_birthdays(self) -> tuple[Birthday, ...]:
        return self._BIRTHDAYS
