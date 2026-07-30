from typing import Protocol

from kletserbot.apps.general.domain.birthdays.birthday import Birthday


class BirthdayProvider(Protocol):
    def retrieve_birthdays(self) -> tuple[Birthday, ...]: ...
