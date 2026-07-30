from dataclasses import dataclass

from kletserbot.domain.cardpacks.pack_configuration import CardFinish
from kletserbot.domain.cardpacks.pokemon_card import PokemonCard


@dataclass(frozen=True, slots=True)
class OpenedCard:
    slot_number: int
    card: PokemonCard
    finish: CardFinish
    is_hit: bool
    is_hidden: bool


@dataclass(frozen=True, slots=True)
class OpenedPack:
    set_id: str
    cards: tuple[OpenedCard, ...]
