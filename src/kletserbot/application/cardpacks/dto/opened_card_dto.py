from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class OpenedCardDto:
    slot_number: int
    card_id: str
    name: str
    number: str
    rarity: str
    finish: str
    image_url: str
    is_hit: bool
    is_hidden: bool
    is_basic_energy: bool
