from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class Birthday:
    person_name: str
    birth_date: date

    def __post_init__(self) -> None:
        normalized_name = self.person_name.strip()
        if not normalized_name:
            raise ValueError("person_name must not be empty")
        object.__setattr__(self, "person_name", normalized_name)
