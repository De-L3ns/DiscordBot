from unittest.mock import AsyncMock

from kletserbot.apps.cardpacks.application.dto.available_card_set_dto import (
    AvailableCardSetDto,
)
from kletserbot.apps.cardpacks.application.dto.collection_card_dto import CollectionSetDto
from kletserbot.apps.cardpacks.application.dto.opened_card_dto import OpenedCardDto
from kletserbot.apps.cardpacks.application.dto.owned_pack_dto import OwnedPackDto
from kletserbot.apps.cardpacks.presentation.discord.cardpacks_cog import CardpacksCog


class FakeCardpackService:
    def __init__(
        self,
        inventory: tuple[OwnedPackDto, ...] = (),
    ) -> None:
        self.inventory = inventory
        self.gifts: list[tuple[int, str, int]] = []

    async def initialize(self) -> None:
        return None

    async def retrieve_inventory(
        self,
        discord_user_id: int,
    ) -> tuple[OwnedPackDto, ...]:
        del discord_user_id
        return self.inventory

    def retrieve_available_sets(self) -> tuple[AvailableCardSetDto, ...]:
        return (
            AvailableCardSetDto(
                set_id="base1",
                set_name="Base Set",
            ),
        )

    async def gift_packs(
        self,
        discord_user_id: int,
        set_id: str,
        amount: int,
    ) -> None:
        self.gifts.append((discord_user_id, set_id, amount))

    async def retrieve_collection_sets(
        self,
        discord_user_id: int,
    ) -> tuple[CollectionSetDto, ...]:
        del discord_user_id
        return (CollectionSetDto("base1", "Base Set", 1, 102),)


class FakePermissions:
    def __init__(self, administrator: bool) -> None:
        self.administrator = administrator


class FakeUser:
    def __init__(self, user_id: int) -> None:
        self.id = user_id
        self.mention = f"<@{user_id}>"


class FakeResponse:
    def __init__(self) -> None:
        self.send_message = AsyncMock()


class FakeInteraction:
    def __init__(self, *, user_id: int, is_administrator: bool = False) -> None:
        self.user = FakeUser(user_id)
        self.permissions = FakePermissions(is_administrator)
        self.response = FakeResponse()
        self.original_response = AsyncMock()


class FakeHitChannel:
    def __init__(self) -> None:
        self.send = AsyncMock()


class FakeBot:
    def __init__(self, channel: FakeHitChannel) -> None:
        self._channel = channel

    def get_channel(self, channel_id: int) -> FakeHitChannel:
        del channel_id
        return self._channel


def test_cardpack_commands_are_declared_with_admin_default() -> None:
    commands = {command.name: command for command in CardpacksCog.__cog_app_commands__}

    assert set(commands) == {"packs", "giftpack", "collection"}
    assert commands["giftpack"].default_permissions is not None
    assert commands["giftpack"].default_permissions.administrator is True


async def test_packs_reports_empty_inventory_ephemerally() -> None:
    cog = CardpacksCog(FakeCardpackService())  # type: ignore[arg-type]
    interaction = FakeInteraction(user_id=123)

    await cog.packs.callback(cog, interaction)  # type: ignore[arg-type]

    interaction.response.send_message.assert_awaited_once_with(
        "Je hebt momenteel geen ongeopende Pokémonpacks.",
        ephemeral=True,
    )


async def test_packs_displays_positive_inventory_with_selection_view() -> None:
    service = FakeCardpackService(
        (
            OwnedPackDto(
                set_id="base1",
                set_name="Base Set",
                quantity=2,
                pack_image_asset="card-pack-image-baseset.jpg",
            ),
        )
    )
    cog = CardpacksCog(service)  # type: ignore[arg-type]
    interaction = FakeInteraction(user_id=123)

    await cog.packs.callback(cog, interaction)  # type: ignore[arg-type]

    call = interaction.response.send_message.await_args
    assert call.kwargs["embed"].title == "Base Set"
    assert call.kwargs["embed"].image.url == "attachment://card-pack-image-baseset.jpg"
    assert call.kwargs["files"][0].filename == "card-pack-image-baseset.jpg"
    assert call.kwargs["ephemeral"] is True
    assert call.kwargs["view"].owner_user_id == 123


async def test_hit_announcement_uses_pulled_and_copy_count_label() -> None:
    channel = FakeHitChannel()
    cog = CardpacksCog(
        FakeCardpackService(),  # type: ignore[arg-type]
        bot=FakeBot(channel),  # type: ignore[arg-type]
        hit_channel_id=456,
    )
    cog._retrieve_hit_collection_details = AsyncMock(return_value=(2, None))

    await cog._announce_hit(
        123,
        "base1",
        OpenedCardDto(
            slot_number=1,
            card_id="base1-4",
            name="Charizard",
            number="4",
            rarity="Rare Holo",
            finish="holo",
            image_url="https://example.com/card.png",
            is_hit=True,
            is_hidden=False,
            is_basic_energy=False,
        ),
    )

    embed = channel.send.await_args.kwargs["embed"]
    assert embed.title == "✨ Er werd een nieuwe hit gepulled!"
    assert embed.description == "<@123> heeft **Charizard** gepulled!"
    assert embed.fields[1].name == "Aantal exemplaren"
    assert embed.fields[1].value == "2×"


async def test_collection_displays_set_picker_ephemerally() -> None:
    cog = CardpacksCog(FakeCardpackService())  # type: ignore[arg-type]
    interaction = FakeInteraction(user_id=123)

    await cog.collection.callback(cog, interaction)  # type: ignore[arg-type]

    call = interaction.response.send_message.await_args
    assert call.kwargs["embed"].title == "Pokémon collection"
    assert call.kwargs["ephemeral"] is True


async def test_non_administrator_cannot_gift_packs() -> None:
    service = FakeCardpackService()
    cog = CardpacksCog(service)  # type: ignore[arg-type]
    interaction = FakeInteraction(user_id=123, is_administrator=False)

    await cog.giftpack.callback(  # type: ignore[arg-type]
        cog,
        interaction,
        FakeUser(456),
        "base1",
        2,
    )

    assert service.gifts == []
    interaction.response.send_message.assert_awaited_once_with(
        "Je hebt beheerdersrechten nodig voor dit commando.",
        ephemeral=True,
    )


async def test_administrator_can_gift_packs() -> None:
    service = FakeCardpackService()
    cog = CardpacksCog(service)  # type: ignore[arg-type]
    interaction = FakeInteraction(user_id=123, is_administrator=True)

    await cog.giftpack.callback(  # type: ignore[arg-type]
        cog,
        interaction,
        FakeUser(456),
        "base1",
        2,
    )

    assert service.gifts == [(456, "base1", 2)]
    interaction.response.send_message.assert_awaited_once_with(
        "🎁 <@456> kreeg 2 × Base Set.",
        ephemeral=True,
    )
