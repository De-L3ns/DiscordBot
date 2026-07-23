from collections.abc import Callable, Sequence
from datetime import date

from kletserbot.application.birthdays.birthday_provider import BirthdayProvider
from kletserbot.application.birthdays.dto.birthday_announcement_dto import (
    BirthdayAnnouncementDto,
)
from kletserbot.domain.birthdays.birthday_calculator import (
    calculate_age_on_date,
    is_birthday_on_date,
)

MessageSelector = Callable[[Sequence[str]], str]


class BirthdayService:
    _THIRTY_MESSAGES = ("Tis voorbij voor u, de 30 is bereikt.",)
    _UNDER_THIRTY_MESSAGES = (
        "Zo oud worden, aleh proficiat er mee hé.",
        "Jahwadde ze, da begint al te tellen.",
    )
    _OVER_THIRTY_MESSAGES = (
        "Dienen, voorbij de 30... Misschien stillekes aan inschrijven "
        "op de wachtlijst van het rusthuis?",
        "In de ogen van de nieuwe generatie zijt gij echt wel al nen ouden ze.",
    )

    def __init__(
        self,
        birthday_provider: BirthdayProvider,
        message_selector: MessageSelector,
    ) -> None:
        self._birthday_provider = birthday_provider
        self._message_selector = message_selector

    def find_announcements(
        self,
        current_date: date,
    ) -> tuple[BirthdayAnnouncementDto, ...]:
        announcements: list[BirthdayAnnouncementDto] = []
        for birthday in self._birthday_provider.retrieve_birthdays():
            if not is_birthday_on_date(birthday, current_date):
                continue

            age = calculate_age_on_date(birthday, current_date)
            message = self._message_selector(self._messages_for_age(age))
            announcements.append(
                BirthdayAnnouncementDto(
                    person_name=birthday.person_name,
                    age=age,
                    announcement_text=(
                        f"{birthday.person_name} is vandaag geboren.\n"
                        f"Gelukkige verjaardag, {birthday.person_name}! "
                        f"{age}!? {message}"
                    ),
                )
            )
        return tuple(announcements)

    def _messages_for_age(self, age: int) -> Sequence[str]:
        if age == 30:
            return self._THIRTY_MESSAGES
        if age > 30:
            return self._OVER_THIRTY_MESSAGES
        return self._UNDER_THIRTY_MESSAGES
