from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CollectionCardDto:
    set_id: str
    set_name: str
    card_id: str
    name: str
    number: str
    rarity: str
    thumbnail_url: str
    image_url: str
    quantity: int


@dataclass(frozen=True, slots=True)
class CollectionSetDto:
    set_id: str
    set_name: str
    collected_cards: int
    total_cards: int


@dataclass(frozen=True, slots=True)
class AlbumCardDto:
    card_id: str
    name: str
    number: str
    rarity: str
    image_url: str
    is_owned: bool
    is_hit: bool
    quantity: int
