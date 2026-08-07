from collections.abc import Sequence

import pytest

from kletserbot.apps.cardpacks.application.cardpack_service import CardpackService
from kletserbot.apps.cardpacks.application.dto.collection_card_dto import CollectionCardDto
from kletserbot.apps.cardpacks.application.dto.pack_inventory_dto import (
    PackInventoryDto,
)
from kletserbot.apps.cardpacks.application.exceptions import (
    CardSetUnavailableError,
    InsufficientPackInventoryError,
    InvalidGiftAmountError,
)
from kletserbot.apps.cardpacks.domain.pack_configuration import (
    CardFinish,
    CardKind,
    CardSetConfiguration,
    PackSlotConfiguration,
    PackSlotOutcome,
)
from kletserbot.apps.cardpacks.domain.pack_generator import PackGenerator
from kletserbot.apps.cardpacks.domain.pokemon_card import PokemonCard
from kletserbot.shared.application.exceptions import ExternalServiceUnavailableError


def common_card(card_id: str = "base1-1") -> PokemonCard:
    return PokemonCard(
        card_id=card_id,
        name="Common Card",
        number="1",
        rarity="Common",
        supertype="Pokémon",
        subtypes=("Basic",),
        small_image_url="https://images.example.test/card.png",
        large_image_url="https://images.example.test/card-large.png",
    )


def collected_card(card_id: str) -> CollectionCardDto:
    return CollectionCardDto(
        set_id="base1",
        set_name="Base Set",
        card_id=card_id,
        name="Collected Card",
        number="1",
        rarity="Common",
        thumbnail_url="https://images.example.test/card.png",
        image_url="https://images.example.test/card-large.png",
        quantity=1,
    )


def configuration(
    outcomes: tuple[PackSlotOutcome, ...] | None = None,
    *,
    energy_set_id: str = "base1",
) -> CardSetConfiguration:
    return CardSetConfiguration(
        set_id="base1",
        name="Base Set",
        pack_image_asset="card-pack-image-baseset.jpg",
        slots=(
            PackSlotConfiguration(
                outcomes=outcomes
                or (
                    PackSlotOutcome(
                        card_kind=CardKind.RARITY,
                        eligible_rarities=("Common",),
                        weight=1.0,
                        finish=CardFinish.NORMAL,
                        is_hit=False,
                    ),
                ),
                is_hidden=False,
            ),
        ),
        energy_set_id=energy_set_id,
    )


class FakeConfigurationProvider:
    def __init__(
        self,
        configurations: tuple[CardSetConfiguration, ...] = (configuration(),),
    ) -> None:
        self._configurations = configurations

    def retrieve_configurations(self) -> tuple[CardSetConfiguration, ...]:
        return self._configurations


class FakeCardCatalog:
    def __init__(
        self,
        *,
        refreshed_cards: tuple[PokemonCard, ...] = (common_card(),),
        cached_cards: tuple[PokemonCard, ...] = (common_card(),),
        refresh_error: Exception | None = None,
        cache_error: Exception | None = None,
        refreshed_cards_by_set: dict[str, tuple[PokemonCard, ...]] | None = None,
        cached_cards_by_set: dict[str, tuple[PokemonCard, ...]] | None = None,
    ) -> None:
        self.refreshed_cards = refreshed_cards
        self.cached_cards = cached_cards
        self.refresh_error = refresh_error
        self.cache_error = cache_error
        self.refreshed_cards_by_set = refreshed_cards_by_set or {}
        self.cached_cards_by_set = cached_cards_by_set or {}
        self.refresh_calls: list[str] = []
        self.cache_calls: list[str] = []

    async def refresh_cards(self, set_id: str) -> tuple[PokemonCard, ...]:
        self.refresh_calls.append(set_id)
        if self.refresh_error is not None:
            raise self.refresh_error
        return self.refreshed_cards_by_set.get(set_id, self.refreshed_cards)

    async def retrieve_cached_cards(
        self,
        set_id: str,
    ) -> tuple[PokemonCard, ...]:
        self.cache_calls.append(set_id)
        if self.cache_error is not None:
            raise self.cache_error
        return self.cached_cards_by_set.get(set_id, self.cached_cards)


class FakeInventoryRepository:
    def __init__(
        self,
        *,
        inventory: tuple[PackInventoryDto, ...] = (),
        consume_result: bool = True,
    ) -> None:
        self.inventory = inventory
        self.consume_result = consume_result
        self.initialize_calls = 0
        self.gifts: list[tuple[int, str, int]] = []
        self.consume_calls: list[tuple[int, str]] = []
        self.collected_cards: list[object] = []

    async def initialize(self) -> None:
        self.initialize_calls += 1

    async def gift_packs(
        self,
        discord_user_id: int,
        set_id: str,
        amount: int,
    ) -> None:
        self.gifts.append((discord_user_id, set_id, amount))

    async def consume_pack(self, discord_user_id: int, set_id: str) -> bool:
        self.consume_calls.append((discord_user_id, set_id))
        return self.consume_result

    async def consume_pack_and_store_cards(
        self,
        discord_user_id: int,
        set_id: str,
        cards: tuple[object, ...],
    ) -> bool:
        self.consume_calls.append((discord_user_id, set_id))
        if self.consume_result:
            self.collected_cards.extend(cards)
        return self.consume_result

    async def retrieve_inventory(
        self,
        discord_user_id: int,
    ) -> tuple[PackInventoryDto, ...]:
        del discord_user_id
        return self.inventory

    async def retrieve_collection(self, discord_user_id: int) -> tuple[object, ...]:
        del discord_user_id
        return tuple(self.collected_cards)


def select_first(cards: Sequence[PokemonCard]) -> PokemonCard:
    return cards[0]


def create_service(
    *,
    configuration_provider: FakeConfigurationProvider | None = None,
    card_catalog: FakeCardCatalog | None = None,
    inventory_repository: FakeInventoryRepository | None = None,
) -> tuple[CardpackService, FakeCardCatalog, FakeInventoryRepository]:
    resolved_catalog = card_catalog or FakeCardCatalog()
    resolved_repository = inventory_repository or FakeInventoryRepository()
    service = CardpackService(
        configuration_provider=configuration_provider or FakeConfigurationProvider(),
        card_catalog=resolved_catalog,
        inventory_repository=resolved_repository,
        pack_generator=PackGenerator(),
        random_value=lambda: 0.0,
        select_card=select_first,
    )
    return service, resolved_catalog, resolved_repository


async def test_initialization_uses_valid_cache_without_refreshing() -> None:
    catalog = FakeCardCatalog(
        refresh_error=ExternalServiceUnavailableError("offline"),
    )
    service, _, repository = create_service(card_catalog=catalog)

    await service.initialize()

    assert service.available_set_ids == ("base1",)
    assert catalog.cache_calls == ["base1"]
    assert catalog.refresh_calls == []
    assert repository.initialize_calls == 1


async def test_initialization_refreshes_when_cache_is_unavailable() -> None:
    catalog = FakeCardCatalog(
        cache_error=ExternalServiceUnavailableError("no cache"),
    )
    service, _, _ = create_service(card_catalog=catalog)

    await service.initialize()

    assert service.available_set_ids == ("base1",)
    assert catalog.cache_calls == ["base1"]
    assert catalog.refresh_calls == ["base1"]


async def test_initialization_disables_set_when_cache_and_refresh_are_unavailable() -> None:
    catalog = FakeCardCatalog(
        refresh_error=ExternalServiceUnavailableError("offline"),
        cache_error=ExternalServiceUnavailableError("no cache"),
    )
    service, _, _ = create_service(card_catalog=catalog)

    await service.initialize()

    assert service.available_set_ids == ()
    assert catalog.cache_calls == ["base1"]
    assert catalog.refresh_calls == ["base1"]


async def test_initialization_disables_set_with_missing_weighted_rarity() -> None:
    weighted_configuration = configuration(
        (
            PackSlotOutcome(
                card_kind=CardKind.RARITY,
                eligible_rarities=("Common",),
                weight=0.5,
                finish=CardFinish.NORMAL,
                is_hit=False,
            ),
            PackSlotOutcome(
                card_kind=CardKind.RARITY,
                eligible_rarities=("Hyper Rare",),
                weight=0.5,
                finish=CardFinish.HOLO,
                is_hit=True,
            ),
        )
    )
    service, _, _ = create_service(
        configuration_provider=FakeConfigurationProvider((weighted_configuration,))
    )

    await service.initialize()

    assert service.available_set_ids == ()


async def test_inventory_returns_only_available_sets_with_display_fields() -> None:
    repository = FakeInventoryRepository(
        inventory=(
            PackInventoryDto(set_id="base1", quantity=2),
            PackInventoryDto(set_id="disabled", quantity=5),
        )
    )
    service, _, _ = create_service(inventory_repository=repository)
    await service.initialize()

    inventory = await service.retrieve_inventory(discord_user_id=123)

    assert len(inventory) == 1
    assert inventory[0].set_id == "base1"
    assert inventory[0].set_name == "Base Set"
    assert inventory[0].quantity == 2
    assert inventory[0].pack_image_asset == "card-pack-image-baseset.jpg"


async def test_collection_summary_counts_only_cards_visible_in_the_album() -> None:
    repository = FakeInventoryRepository()
    repository.collected_cards.extend(
        (collected_card("base1-1"), collected_card("base1-stale-card"))
    )
    service, _, _ = create_service(inventory_repository=repository)
    await service.initialize()

    summaries = await service.retrieve_collection_sets(discord_user_id=123)

    assert summaries[0].collected_cards == 1
    assert summaries[0].total_cards == 1


async def test_gift_validates_set_and_amount_before_writing() -> None:
    service, _, repository = create_service()
    await service.initialize()

    with pytest.raises(InvalidGiftAmountError):
        await service.gift_packs(123, "base1", 0)
    with pytest.raises(CardSetUnavailableError):
        await service.gift_packs(123, "unknown", 1)

    assert repository.gifts == []


async def test_open_pack_generates_then_consumes_and_returns_dto() -> None:
    service, catalog, repository = create_service()
    await service.initialize()
    catalog.cached_cards = (common_card("base1-2"),)

    opened_pack = await service.open_pack(discord_user_id=123, set_id="base1")

    assert repository.consume_calls == [(123, "base1")]
    assert opened_pack.set_name == "Base Set"
    assert opened_pack.cards[0].card_id == "base1-2"
    assert opened_pack.cards[0].is_hidden is False


async def test_generation_failure_does_not_consume_inventory() -> None:
    service, catalog, repository = create_service()
    await service.initialize()
    catalog.cached_cards = ()

    with pytest.raises(CardSetUnavailableError):
        await service.open_pack(discord_user_id=123, set_id="base1")

    assert repository.consume_calls == []


async def test_failed_conditional_consumption_discards_generated_pack() -> None:
    repository = FakeInventoryRepository(consume_result=False)
    service, _, _ = create_service(inventory_repository=repository)
    await service.initialize()

    with pytest.raises(InsufficientPackInventoryError):
        await service.open_pack(discord_user_id=123, set_id="base1")


async def test_external_energy_set_is_synchronized_and_used_for_opening() -> None:
    energy_outcome = PackSlotOutcome(
        card_kind=CardKind.BASIC_ENERGY,
        eligible_rarities=(),
        weight=1.0,
        finish=CardFinish.NORMAL,
        is_hit=False,
    )
    configured_set = CardSetConfiguration(
        set_id="sv3pt5",
        name="151",
        pack_image_asset="card-pack-image-151.webp",
        slots=(
            PackSlotConfiguration(
                outcomes=(
                    PackSlotOutcome(
                        card_kind=CardKind.RARITY,
                        eligible_rarities=("Common",),
                        weight=1.0,
                        finish=CardFinish.NORMAL,
                        is_hit=False,
                    ),
                ),
                is_hidden=False,
            ),
            PackSlotConfiguration(
                outcomes=(energy_outcome,),
                is_hidden=False,
            ),
        ),
        energy_set_id="sve",
        energy_card_ids=("sve-1",),
    )
    energy_card = PokemonCard(
        card_id="sve-1",
        name="Basic Grass Energy",
        number="1",
        rarity="Common",
        supertype="Energy",
        subtypes=("Basic",),
        small_image_url="https://images.example.test/energy.png",
        large_image_url="https://images.example.test/energy-large.png",
    )
    catalog = FakeCardCatalog(
        refreshed_cards_by_set={
            "sv3pt5": (common_card("sv3pt5-1"),),
            "sve": (energy_card,),
        },
        cached_cards_by_set={
            "sv3pt5": (common_card("sv3pt5-1"),),
            "sve": (energy_card,),
        },
    )
    service, _, _ = create_service(
        configuration_provider=FakeConfigurationProvider((configured_set,)),
        card_catalog=catalog,
    )

    await service.initialize()
    opened_pack = await service.open_pack(123, "sv3pt5")

    assert service.available_set_ids == ("sv3pt5",)
    assert catalog.refresh_calls == []
    assert catalog.cache_calls == ["sv3pt5", "sve", "sv3pt5", "sve"]
    assert opened_pack.cards[1].card_id == "sve-1"
    assert opened_pack.cards[1].is_basic_energy is True
