from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BirthdayAnnouncementDto:
    person_name: str
    age: int
    announcement_text: str
