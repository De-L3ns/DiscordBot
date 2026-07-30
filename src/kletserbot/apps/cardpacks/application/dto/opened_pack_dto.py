from dataclasses import dataclass

from kletserbot.apps.cardpacks.application.dto.opened_card_dto import OpenedCardDto


@dataclass(frozen=True, slots=True)
class OpenedPackDto:
    set_id: str
    set_name: str
    cards: tuple[OpenedCardDto, ...]
