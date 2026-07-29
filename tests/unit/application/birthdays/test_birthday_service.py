from collections.abc import Sequence
from datetime import date

from kletserbot.application.birthdays.birthday_service import BirthdayService
from kletserbot.domain.birthdays.birthday import Birthday


class FakeBirthdayProvider:
    def retrieve_birthdays(self) -> tuple[Birthday, ...]:
        return (
            Birthday("Laurens", date(1993, 7, 21)),
            Birthday("Someone Else", date(1990, 6, 1)),
        )


def select_first(messages: Sequence[str]) -> str:
    return messages[0]


def test_service_returns_only_birthdays_matching_today() -> None:
    service = BirthdayService(FakeBirthdayProvider(), select_first)

    results = service.find_announcements(date(2026, 7, 21))

    assert tuple(result.person_name for result in results) == ("Laurens",)
    assert results[0].age == 33
    assert "Laurens is vandaag geboren" in results[0].announcement_text
    assert "@everyone" not in results[0].announcement_text


def test_service_returns_no_announcements_without_a_match() -> None:
    service = BirthdayService(FakeBirthdayProvider(), select_first)

    assert service.find_announcements(date(2026, 7, 22)) == ()


def test_thirtieth_birthday_uses_thirty_message() -> None:
    service = BirthdayService(FakeBirthdayProvider(), select_first)

    result = service.find_announcements(date(2023, 7, 21))[0]

    assert "30 is bereikt" in result.announcement_text
