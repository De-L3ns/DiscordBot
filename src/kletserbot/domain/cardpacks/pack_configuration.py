import math
from dataclasses import dataclass
from enum import StrEnum

from kletserbot.domain.cardpacks.pokemon_card import PokemonCard


class InvalidPackConfigurationError(ValueError):
    """Raised when a configured card set cannot produce valid packs."""


class CardKind(StrEnum):
    RARITY = "rarity"
    BASIC_ENERGY = "basic_energy"


class CardFinish(StrEnum):
    NORMAL = "normal"
    REVERSE_HOLO = "reverse_holo"
    HOLO = "holo"


@dataclass(frozen=True, slots=True)
class PackSlotOutcome:
    card_kind: CardKind
    eligible_rarities: tuple[str, ...]
    weight: float
    finish: CardFinish
    is_hit: bool

    def __post_init__(self) -> None:
        if not math.isfinite(self.weight) or self.weight <= 0 or self.weight > 1:
            raise InvalidPackConfigurationError(
                "slot outcome weight must be greater than 0 and at most 1"
            )
        if self.card_kind is CardKind.BASIC_ENERGY:
            if self.eligible_rarities:
                raise InvalidPackConfigurationError(
                    "Basic Energy outcomes cannot declare eligible rarities"
                )
            return
        if not self.eligible_rarities or any(
            not rarity.strip() for rarity in self.eligible_rarities
        ):
            raise InvalidPackConfigurationError(
                "rarity outcomes require non-empty eligible rarities"
            )

    def filter_eligible_cards(
        self,
        cards: tuple[PokemonCard, ...],
    ) -> tuple[PokemonCard, ...]:
        if self.card_kind is CardKind.BASIC_ENERGY:
            return tuple(card for card in cards if card.is_basic_energy)

        return tuple(
            card
            for card in cards
            if not card.is_basic_energy and card.rarity in self.eligible_rarities
        )

    @property
    def requires_unique_normal_card(self) -> bool:
        return (
            self.card_kind is CardKind.RARITY
            and self.finish is CardFinish.NORMAL
            and len(self.eligible_rarities) == 1
            and self.eligible_rarities[0] in {"Common", "Uncommon"}
        )


@dataclass(frozen=True, slots=True)
class PackSlotConfiguration:
    outcomes: tuple[PackSlotOutcome, ...]
    is_hidden: bool

    def __post_init__(self) -> None:
        if not self.outcomes:
            raise InvalidPackConfigurationError("slot requires at least one outcome")
        total_weight = math.fsum(outcome.weight for outcome in self.outcomes)
        if not math.isclose(total_weight, 1.0, rel_tol=0, abs_tol=1e-9):
            raise InvalidPackConfigurationError("slot outcome weights must total 1.0")

    def select_outcome(self, random_value: float) -> PackSlotOutcome:
        if not math.isfinite(random_value) or not 0 <= random_value < 1:
            raise ValueError("random value must be at least 0 and less than 1")

        cumulative_weight = 0.0
        for outcome in self.outcomes:
            cumulative_weight += outcome.weight
            if random_value < cumulative_weight:
                return outcome
        return self.outcomes[-1]


@dataclass(frozen=True, slots=True)
class CardSetConfiguration:
    set_id: str
    name: str
    pack_image_asset: str
    slots: tuple[PackSlotConfiguration, ...]
    energy_set_id: str | None = None
    energy_card_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.set_id.strip():
            raise InvalidPackConfigurationError("set ID must not be empty")
        if not self.name.strip():
            raise InvalidPackConfigurationError("set name must not be empty")
        if not self.pack_image_asset.strip():
            raise InvalidPackConfigurationError("pack image asset must not be empty")
        if not self.slots:
            raise InvalidPackConfigurationError("card set requires at least one slot")
        if self.energy_set_id is not None and not self.energy_set_id.strip():
            raise InvalidPackConfigurationError("energy set ID must not be empty")
        if any(not card_id.strip() for card_id in self.energy_card_ids):
            raise InvalidPackConfigurationError("energy card IDs must not be empty")
        if len(set(self.energy_card_ids)) != len(self.energy_card_ids):
            raise InvalidPackConfigurationError("energy card IDs must be unique")

    @property
    def resolved_energy_set_id(self) -> str:
        return self.energy_set_id or self.set_id
