from typing import Protocol

from kletserbot.domain.birthdays.birthday import Birthday


class BirthdayProvider(Protocol):
    def retrieve_birthdays(self) -> tuple[Birthday, ...]: ...
