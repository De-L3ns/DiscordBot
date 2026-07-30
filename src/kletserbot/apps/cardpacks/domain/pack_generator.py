from collections.abc import Callable, Sequence

from kletserbot.apps.cardpacks.domain.opened_pack import OpenedCard, OpenedPack
from kletserbot.apps.cardpacks.domain.pack_configuration import (
    CardSetConfiguration,
    PackSlotOutcome,
)
from kletserbot.apps.cardpacks.domain.pokemon_card import PokemonCard


class InsufficientCardPoolError(ValueError):
    """Raised when cached cards cannot fill a configured pack slot."""


class InvalidCardSelectionError(ValueError):
    """Raised when an injected selector returns a card outside its candidates."""


class PackGenerator:
    @staticmethod
    def _filter_configured_cards(
        configuration: CardSetConfiguration,
        cards: Sequence[PokemonCard],
    ) -> tuple[PokemonCard, ...]:
        energy_card_ids = frozenset(configuration.energy_card_ids)
        return tuple(
            card for card in cards if not card.is_basic_energy or card.card_id in energy_card_ids
        )

    def validate_card_pool(
        self,
        configuration: CardSetConfiguration,
        cards: Sequence[PokemonCard],
    ) -> None:
        available_cards = self._filter_configured_cards(configuration, cards)
        unique_requirements: dict[
            tuple[str, tuple[str, ...], str],
            int,
        ] = {}
        unique_outcomes: dict[
            tuple[str, tuple[str, ...], str],
            PackSlotOutcome,
        ] = {}

        for slot_number, slot in enumerate(configuration.slots, start=1):
            for outcome in slot.outcomes:
                if not outcome.filter_eligible_cards(available_cards):
                    raise InsufficientCardPoolError(f"slot {slot_number} has no eligible cards")
                if outcome.requires_unique_normal_card:
                    requirement_key = (
                        outcome.card_kind.value,
                        outcome.eligible_rarities,
                        outcome.finish.value,
                    )
                    unique_requirements[requirement_key] = (
                        unique_requirements.get(requirement_key, 0) + 1
                    )
                    unique_outcomes[requirement_key] = outcome

        for requirement_key, required_count in unique_requirements.items():
            outcome = unique_outcomes[requirement_key]
            eligible_card_ids = {
                card.card_id for card in outcome.filter_eligible_cards(available_cards)
            }
            if len(eligible_card_ids) < required_count:
                raise InsufficientCardPoolError(
                    "configured unique slots have too few eligible cards"
                )

    def generate_pack(
        self,
        configuration: CardSetConfiguration,
        cards: Sequence[PokemonCard],
        random_value: Callable[[], float],
        select_card: Callable[[Sequence[PokemonCard]], PokemonCard],
    ) -> OpenedPack:
        available_cards = self._filter_configured_cards(configuration, cards)
        opened_cards: list[OpenedCard] = []
        used_unique_card_ids: set[str] = set()

        for slot_number, slot in enumerate(configuration.slots, start=1):
            outcome = (
                slot.outcomes[0] if len(slot.outcomes) == 1 else slot.select_outcome(random_value())
            )
            eligible_cards = outcome.filter_eligible_cards(available_cards)
            if outcome.requires_unique_normal_card:
                eligible_cards = tuple(
                    card for card in eligible_cards if card.card_id not in used_unique_card_ids
                )
            if not eligible_cards:
                raise InsufficientCardPoolError(f"slot {slot_number} has no eligible cards")

            selected_card = select_card(eligible_cards)
            if selected_card not in eligible_cards:
                raise InvalidCardSelectionError(
                    f"selector returned an ineligible card for slot {slot_number}"
                )
            if outcome.requires_unique_normal_card:
                used_unique_card_ids.add(selected_card.card_id)

            opened_cards.append(
                OpenedCard(
                    slot_number=slot_number,
                    card=selected_card,
                    finish=outcome.finish,
                    is_hit=outcome.is_hit,
                    is_hidden=slot.is_hidden,
                )
            )

        return OpenedPack(
            set_id=configuration.set_id,
            cards=tuple(opened_cards),
        )
