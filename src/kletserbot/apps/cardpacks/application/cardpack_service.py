import asyncio
import logging
import re
from collections.abc import Callable, Sequence

from kletserbot.apps.cardpacks.application.card_set_configuration_provider import (
    CardSetConfigurationProvider,
)
from kletserbot.apps.cardpacks.application.dto.available_card_set_dto import (
    AvailableCardSetDto,
)
from kletserbot.apps.cardpacks.application.dto.collection_card_dto import (
    AlbumCardDto,
    CollectionCardDto,
    CollectionSetDto,
)
from kletserbot.apps.cardpacks.application.dto.opened_card_dto import OpenedCardDto
from kletserbot.apps.cardpacks.application.dto.opened_pack_dto import OpenedPackDto
from kletserbot.apps.cardpacks.application.dto.owned_pack_dto import OwnedPackDto
from kletserbot.apps.cardpacks.application.exceptions import (
    CardpackConfigurationError,
    CardSetUnavailableError,
    InsufficientPackInventoryError,
    InvalidGiftAmountError,
)
from kletserbot.apps.cardpacks.application.pack_inventory_repository import (
    PackInventoryRepository,
)
from kletserbot.apps.cardpacks.application.pokemon_card_catalog_gateway import (
    PokemonCardCatalogGateway,
)
from kletserbot.apps.cardpacks.domain.opened_pack import OpenedPack
from kletserbot.apps.cardpacks.domain.pack_configuration import CardSetConfiguration
from kletserbot.apps.cardpacks.domain.pack_generator import (
    InsufficientCardPoolError,
    PackGenerator,
)
from kletserbot.apps.cardpacks.domain.pokemon_card import PokemonCard
from kletserbot.shared.application.exceptions import ApplicationError

logger = logging.getLogger(__name__)

_MAX_GIFT_AMOUNT = 100


class CardpackService:
    def __init__(
        self,
        *,
        configuration_provider: CardSetConfigurationProvider,
        card_catalog: PokemonCardCatalogGateway,
        inventory_repository: PackInventoryRepository,
        pack_generator: PackGenerator,
        random_value: Callable[[], float],
        select_card: Callable[[Sequence[PokemonCard]], PokemonCard],
    ) -> None:
        self._configuration_provider = configuration_provider
        self._card_catalog = card_catalog
        self._inventory_repository = inventory_repository
        self._pack_generator = pack_generator
        self._random_value = random_value
        self._select_card = select_card
        self._available_configurations: dict[str, CardSetConfiguration] = {}
        self._cards_by_source_set_id: dict[str, tuple[PokemonCard, ...]] = {}

    async def initialize(self) -> None:
        await self._inventory_repository.initialize()
        try:
            configurations = await asyncio.to_thread(
                self._configuration_provider.retrieve_configurations
            )
        except CardpackConfigurationError:
            logger.exception("cardpack_configuration_load_failed")
            self._available_configurations = {}
            return

        available_configurations: dict[str, CardSetConfiguration] = {}
        synchronized_cards_by_set_id: dict[str, tuple[PokemonCard, ...]] = {}
        for configuration in configurations:
            primary_cards = await self._retrieve_synchronized_cards(
                configuration.set_id,
                synchronized_cards_by_set_id,
            )
            if primary_cards is None:
                continue
            cards = primary_cards
            if configuration.resolved_energy_set_id != configuration.set_id:
                energy_cards = await self._retrieve_synchronized_cards(
                    configuration.resolved_energy_set_id,
                    synchronized_cards_by_set_id,
                )
                if energy_cards is None:
                    continue
                cards += energy_cards
            try:
                self._pack_generator.validate_card_pool(configuration, cards)
            except InsufficientCardPoolError as error:
                logger.warning(
                    "cardpack_card_pool_invalid set_id=%s reason=%s",
                    configuration.set_id,
                    error,
                )
                continue
            available_configurations[configuration.set_id] = configuration
        self._available_configurations = available_configurations
        self._cards_by_source_set_id = synchronized_cards_by_set_id

    @property
    def available_set_ids(self) -> tuple[str, ...]:
        return tuple(self._available_configurations)

    def retrieve_available_sets(self) -> tuple[AvailableCardSetDto, ...]:
        return tuple(
            AvailableCardSetDto(
                set_id=configuration.set_id,
                set_name=configuration.name,
            )
            for configuration in self._available_configurations.values()
        )

    async def retrieve_inventory(
        self,
        discord_user_id: int,
    ) -> tuple[OwnedPackDto, ...]:
        inventory = await self._inventory_repository.retrieve_inventory(discord_user_id)
        owned_packs: list[OwnedPackDto] = []
        for entry in inventory:
            configuration = self._available_configurations.get(entry.set_id)
            if configuration is not None and entry.quantity > 0:
                owned_packs.append(
                    OwnedPackDto(
                        set_id=entry.set_id,
                        set_name=configuration.name,
                        quantity=entry.quantity,
                        pack_image_asset=configuration.pack_image_asset,
                    )
                )
        return tuple(owned_packs)

    async def gift_packs(
        self,
        discord_user_id: int,
        set_id: str,
        amount: int,
    ) -> None:
        if not 1 <= amount <= _MAX_GIFT_AMOUNT:
            raise InvalidGiftAmountError(f"gift amount must be between 1 and {_MAX_GIFT_AMOUNT}")
        self._require_available_configuration(set_id)
        await self._inventory_repository.gift_packs(
            discord_user_id,
            set_id,
            amount,
        )

    async def open_pack(
        self,
        discord_user_id: int,
        set_id: str,
    ) -> OpenedPackDto:
        configuration = self._require_available_configuration(set_id)
        try:
            primary_cards = await self._card_catalog.retrieve_cached_cards(set_id)
            cards = primary_cards
            if configuration.resolved_energy_set_id != set_id:
                energy_cards = await self._card_catalog.retrieve_cached_cards(
                    configuration.resolved_energy_set_id
                )
                cards += energy_cards
            opened_pack = self._pack_generator.generate_pack(
                configuration,
                cards,
                self._random_value,
                self._select_card,
            )
        except (ApplicationError, InsufficientCardPoolError) as error:
            raise CardSetUnavailableError(f"card set is currently unavailable: {set_id}") from error

        collected_cards = tuple(
            CollectionCardDto(
                set_id=configuration.set_id,
                set_name=configuration.name,
                card_id=opened_card.card.card_id,
                name=opened_card.card.name,
                number=opened_card.card.number,
                rarity=opened_card.card.rarity,
                thumbnail_url=opened_card.card.small_image_url,
                image_url=opened_card.card.large_image_url,
                quantity=1,
            )
            for opened_card in opened_pack.cards
        )
        was_consumed = await self._inventory_repository.consume_pack_and_store_cards(
            discord_user_id,
            set_id,
            collected_cards,
        )
        if not was_consumed:
            raise InsufficientPackInventoryError("the user no longer owns this pack")
        return _map_opened_pack(opened_pack, configuration.name)

    async def retrieve_collection_sets(
        self,
        discord_user_id: int,
    ) -> tuple[CollectionSetDto, ...]:
        collected_cards = await self._inventory_repository.retrieve_collection(discord_user_id)
        summaries: list[CollectionSetDto] = []
        collected_card_ids_by_set: dict[str, set[str]] = {}
        for card in collected_cards:
            collected_card_ids_by_set.setdefault(card.set_id, set()).add(card.card_id)
        for configuration in self._available_configurations.values():
            candidates = await self._retrieve_collection_candidates(configuration)
            collected_candidate_ids = collected_card_ids_by_set.get(
                configuration.set_id,
                set(),
            ).intersection(candidates)
            summaries.append(
                CollectionSetDto(
                    set_id=configuration.set_id,
                    set_name=configuration.name,
                    collected_cards=len(collected_candidate_ids),
                    total_cards=len(candidates),
                )
            )
        return tuple(sorted(summaries, key=lambda summary: summary.set_name))

    async def retrieve_album_cards(
        self,
        discord_user_id: int,
        set_id: str,
    ) -> tuple[AlbumCardDto, ...]:
        cards = await self._inventory_repository.retrieve_collection(discord_user_id)
        owned_cards = {card.card_id: card for card in cards if card.set_id == set_id}
        configuration = self._available_configurations.get(set_id)
        if configuration is None:
            return ()
        candidates = await self._retrieve_collection_candidates(configuration)
        return tuple(
            AlbumCardDto(
                card_id=card_id,
                name=card.name,
                number=card.number,
                rarity=card.rarity,
                image_url=card.large_image_url,
                is_owned=card_id in owned_cards,
                is_hit=is_hit,
                quantity=owned_cards[card_id].quantity if card_id in owned_cards else 0,
            )
            for card_id, (card, is_hit) in sorted(
                candidates.items(),
                key=lambda candidate: (
                    _card_number_sort_key(candidate[1][0].number), candidate[1][0].name
                ),
            )
        )

    async def _retrieve_collection_candidates(
        self,
        configuration: CardSetConfiguration,
    ) -> dict[str, tuple[PokemonCard, bool]]:
        primary_cards = self._cards_by_source_set_id.get(configuration.set_id)
        if primary_cards is None:
            primary_cards = await self._card_catalog.retrieve_cached_cards(configuration.set_id)
            self._cards_by_source_set_id[configuration.set_id] = primary_cards
        cards = primary_cards
        if configuration.resolved_energy_set_id != configuration.set_id:
            energy_set_id = configuration.resolved_energy_set_id
            energy_cards = self._cards_by_source_set_id.get(energy_set_id)
            if energy_cards is None:
                energy_cards = await self._card_catalog.retrieve_cached_cards(energy_set_id)
                self._cards_by_source_set_id[energy_set_id] = energy_cards
            cards += energy_cards
        allowed_energy_ids = frozenset(configuration.energy_card_ids)
        candidates: dict[str, tuple[PokemonCard, bool]] = {}
        for slot in configuration.slots:
            for outcome in slot.outcomes:
                for card in outcome.filter_eligible_cards(cards):
                    if card.is_basic_energy and card.card_id not in allowed_energy_ids:
                        continue
                    existing = candidates.get(card.card_id)
                    candidates[card.card_id] = (
                        card,
                        outcome.is_hit or (existing is not None and existing[1]),
                    )
        return candidates

    async def _refresh_or_retrieve_cached_cards(
        self,
        set_id: str,
    ) -> tuple[PokemonCard, ...] | None:
        try:
            return await self._card_catalog.retrieve_cached_cards(set_id)
        except ApplicationError as cache_error:
            logger.warning(
                "cardpack_cache_unavailable set_id=%s reason=%s",
                set_id,
                cache_error,
            )
        try:
            return await self._card_catalog.refresh_cards(set_id)
        except ApplicationError as refresh_error:
            logger.warning(
                "cardpack_set_refresh_failed set_id=%s reason=%s",
                set_id,
                refresh_error,
            )
            return None

    async def _retrieve_synchronized_cards(
        self,
        source_set_id: str,
        synchronized_cards_by_set_id: dict[str, tuple[PokemonCard, ...]],
    ) -> tuple[PokemonCard, ...] | None:
        if source_set_id in synchronized_cards_by_set_id:
            return synchronized_cards_by_set_id[source_set_id]
        cards = await self._refresh_or_retrieve_cached_cards(source_set_id)
        if cards is not None:
            synchronized_cards_by_set_id[source_set_id] = cards
        return cards

    def _require_available_configuration(
        self,
        set_id: str,
    ) -> CardSetConfiguration:
        configuration = self._available_configurations.get(set_id)
        if configuration is None:
            raise CardSetUnavailableError(f"card set is currently unavailable: {set_id}")
        return configuration


def _card_number_sort_key(number: str) -> tuple[tuple[int, int | str], ...]:
    return tuple(
        (0, int(part)) if part.isdecimal() else (1, part.casefold())
        for part in re.findall(r"\d+|\D+", number)
    )


def _map_opened_pack(
    opened_pack: OpenedPack,
    set_name: str,
) -> OpenedPackDto:
    return OpenedPackDto(
        set_id=opened_pack.set_id,
        set_name=set_name,
        cards=tuple(
            OpenedCardDto(
                slot_number=opened_card.slot_number,
                card_id=opened_card.card.card_id,
                name=opened_card.card.name,
                number=opened_card.card.number,
                rarity=opened_card.card.rarity,
                finish=opened_card.finish,
                image_url=opened_card.card.large_image_url,
                is_hit=opened_card.is_hit,
                is_hidden=opened_card.is_hidden,
                is_basic_energy=opened_card.card.is_basic_energy,
            )
            for opened_card in opened_pack.cards
        ),
    )
