import struct
from pathlib import Path
from unittest.mock import AsyncMock

import discord

from kletserbot.apps.cardpacks.application.dto.opened_card_dto import OpenedCardDto
from kletserbot.apps.cardpacks.application.dto.opened_pack_dto import OpenedPackDto
from kletserbot.apps.cardpacks.application.dto.owned_pack_dto import OwnedPackDto
from kletserbot.apps.cardpacks.presentation.discord.cardpack_views import (
    CardRevealView,
    InventorySelectionView,
    build_pack_result_content,
)

PROJECT_ROOT = Path(__file__).parents[6]


def opened_pack() -> OpenedPackDto:
    return OpenedPackDto(
        set_id="sv3pt5",
        set_name="Scarlet & Violet—151",
        cards=tuple(
            OpenedCardDto(
                slot_number=slot_number,
                card_id=f"sv3pt5-{slot_number}",
                name=f"Card {slot_number}",
                number=str(slot_number),
                rarity="Illustration Rare" if slot_number == 9 else "Common",
                finish="holo" if slot_number == 9 else "normal",
                image_url=f"https://images.example.test/{slot_number}.png",
                is_hit=slot_number == 9,
                is_hidden=slot_number in {8, 9, 10},
                is_basic_energy=slot_number == 11,
            )
            for slot_number in range(1, 12)
        ),
    )


class FakeUser:
    def __init__(self, user_id: int) -> None:
        self.id = user_id


class FakeResponse:
    def __init__(self) -> None:
        self.send_message = AsyncMock()
        self.edit_message = AsyncMock()
        self.defer = AsyncMock()


class FakeFollowup:
    def __init__(self) -> None:
        self.send = AsyncMock()


class FakeInteraction:
    def __init__(self, user_id: int) -> None:
        self.user = FakeUser(user_id)
        self.response = FakeResponse()
        self.followup = FakeFollowup()
        self.edit_original_response = AsyncMock(return_value=AsyncMock())
        self.message = None


def owned_pack(
    set_id: str,
    set_name: str,
    quantity: int,
) -> OwnedPackDto:
    asset_names = {
        "sv3pt5": "card-pack-image-151.webp",
        "base1": "card-pack-image-baseset.jpg",
    }
    return OwnedPackDto(
        set_id=set_id,
        set_name=set_name,
        quantity=quantity,
        pack_image_asset=asset_names[set_id],
    )


def test_inventory_shows_pack_logo_and_immediate_open_without_dropdown() -> None:
    view = InventorySelectionView(
        owner_user_id=123,
        cardpack_service=AsyncMock(),
        owned_packs=(owned_pack("sv3pt5", "151", 2),),
    )

    assert view.embed.title == "151"
    assert view.embed.description == "Je hebt nog **2** pack(s)."
    assert view.embed.image.url == "attachment://card-pack-image-151.webp"
    assert view.pack_image_file.filename == "card-pack-image-151.webp"
    assert all(not isinstance(child, discord.ui.Select) for child in view.children)
    assert [child.label for child in view.children] == ["Open pack"]


async def test_inventory_navigation_updates_logo_and_open_target() -> None:
    view = InventorySelectionView(
        owner_user_id=123,
        cardpack_service=AsyncMock(),
        owned_packs=(
            owned_pack("sv3pt5", "151", 2),
            owned_pack("base1", "Base Set", 1),
        ),
    )
    interaction = FakeInteraction(user_id=123)

    await view.change_page(
        interaction,  # type: ignore[arg-type]
        page_delta=1,
    )

    assert view.embed.title == "Base Set"
    edited_embed = interaction.response.edit_message.await_args.kwargs["embed"]
    assert edited_embed.image.url == "attachment://card-pack-image-baseset.jpg"
    assert (
        interaction.response.edit_message.await_args.kwargs["attachments"][0].filename
        == "card-pack-image-baseset.jpg"
    )
    open_button = next(child for child in view.children if child.label == "Open pack")
    assert open_button.custom_id == "cardpack:open:base1"


def reveal_view(
    service: AsyncMock | None = None,
) -> CardRevealView:
    return CardRevealView(
        owner_user_id=123,
        cardpack_service=service or AsyncMock(),
        opened_pack=opened_pack(),
    )


async def move_to_slot(view: CardRevealView, slot_number: int) -> FakeInteraction:
    interaction = FakeInteraction(user_id=123)
    while view.current_card.slot_number < slot_number:
        await view.change_card(
            interaction,  # type: ignore[arg-type]
            page_delta=1,
        )
    return interaction


async def reveal_all_hidden_cards(view: CardRevealView) -> None:
    for slot_number in (8, 9, 10):
        interaction = await move_to_slot(view, slot_number)
        await view.reveal_current_card(interaction)  # type: ignore[arg-type]


def test_reveal_view_starts_with_one_regular_card_and_no_energy_page() -> None:
    view = reveal_view()

    assert view.current_card.slot_number == 1
    assert view.current_embed.title == "Kaart 1 — Card 1"
    assert len(view.display_cards) == 10
    assert all(not card.is_basic_energy for card in view.display_cards)
    assert [child.label for child in view.children] == ["Vorige", "Volgende"]
    assert view.children[0].disabled is True


async def test_card_navigation_edits_message_with_exactly_one_card() -> None:
    view = reveal_view()
    interaction = FakeInteraction(user_id=123)

    await view.change_card(
        interaction,  # type: ignore[arg-type]
        page_delta=1,
    )

    assert view.current_card.slot_number == 2
    edit_call = interaction.response.edit_message.await_args
    assert edit_call.kwargs["embed"].title == "Kaart 2 — Card 2"
    assert "embeds" not in edit_call.kwargs


async def test_hidden_card_uses_kletserbot_back_and_blocks_next() -> None:
    view = reveal_view()

    interaction = await move_to_slot(view, 8)

    assert view.current_embed.title == "Kaart 8 — Verborgen"
    assert view.current_embed.image.url == "attachment://kletserbot-card-back.png"
    attachments = interaction.response.edit_message.await_args.kwargs["attachments"]
    assert attachments[0].filename == "kletserbot-card-back.png"
    controls = {child.label: child for child in view.children}
    assert controls["Onthul kaart"].disabled is False
    assert controls["Volgende"].disabled is True


async def test_revealing_card_removes_back_attachment() -> None:
    view = reveal_view()
    await move_to_slot(view, 8)
    interaction = FakeInteraction(123)

    await view.reveal_current_card(interaction)  # type: ignore[arg-type]

    edit_call = interaction.response.edit_message.await_args
    assert edit_call.kwargs["embed"].image.url.endswith("/8.png")
    assert edit_call.kwargs["attachments"] == []


def test_card_back_uses_standard_trading_card_aspect_ratio() -> None:
    card_back_path = (
        PROJECT_ROOT
        / "src"
        / "kletserbot"
        / "apps"
        / "cardpacks"
        / "assets"
        / "discord"
        / "kletserbot-card-back.png"
    )
    width, height = struct.unpack(">II", card_back_path.read_bytes()[16:24])

    assert width * 7 == height * 5


def test_pack_result_reports_energy_as_text() -> None:
    content = build_pack_result_content(opened_pack())

    assert content == "You opened a pack of: Scarlet & Violet—151. The energy card was: Card 11."


async def test_other_user_cannot_reveal_card() -> None:
    view = reveal_view()
    interaction = FakeInteraction(user_id=456)

    is_allowed = await view.interaction_check(interaction)  # type: ignore[arg-type]

    assert is_allowed is False
    interaction.response.send_message.assert_awaited_once_with(
        "Alleen de eigenaar van dit pack kan deze kaarten onthullen.",
        ephemeral=True,
    )


async def test_revealed_hit_uses_celebratory_styling() -> None:
    view = reveal_view()
    await move_to_slot(view, 8)
    await view.reveal_current_card(FakeInteraction(123))  # type: ignore[arg-type]
    await view.change_card(FakeInteraction(123), 1)  # type: ignore[arg-type]

    interaction = FakeInteraction(123)
    await view.reveal_current_card(interaction)  # type: ignore[arg-type]

    assert view.revealed_slot_numbers == frozenset({8, 9})
    assert (
        interaction.response.edit_message.await_args.kwargs["embed"].title
        == "✨ HIT! Kaart 9 — Card 9"
    )
    assert view.current_embed.colour == discord.Colour.gold()


async def test_open_another_pack_appears_only_after_last_reveal_when_pack_remains() -> None:
    service = AsyncMock()
    service.retrieve_inventory.return_value = (owned_pack("sv3pt5", "151", 1),)
    view = reveal_view(service)

    await reveal_all_hidden_cards(view)

    assert "Open another pack" in [child.label for child in view.children]


async def test_open_another_pack_stays_hidden_when_inventory_is_empty() -> None:
    service = AsyncMock()
    service.retrieve_inventory.return_value = ()
    view = reveal_view(service)

    await reveal_all_hidden_cards(view)

    assert "Open another pack" not in [child.label for child in view.children]


async def test_open_another_pack_replaces_result_and_restarts_reveal() -> None:
    service = AsyncMock()
    service.retrieve_inventory.return_value = (owned_pack("sv3pt5", "151", 1),)
    service.open_pack.return_value = opened_pack()
    view = reveal_view(service)
    await reveal_all_hidden_cards(view)
    open_another_button = next(
        child for child in view.children if child.label == "Open another pack"
    )
    interaction = FakeInteraction(user_id=123)

    await open_another_button.callback(interaction)  # type: ignore[arg-type]

    edit_call = interaction.edit_original_response.await_args
    assert edit_call.kwargs["content"].startswith("You opened a pack of: Scarlet & Violet—151.")
    assert edit_call.kwargs["embed"].title == "Kaart 1 — Card 1"
    assert edit_call.kwargs["attachments"] == []
    replacement_view = edit_call.kwargs["view"]
    assert [child.label for child in replacement_view.children] == ["Vorige", "Volgende"]


async def test_timeout_disables_controls_on_the_discord_message() -> None:
    view = reveal_view()
    message = AsyncMock()
    view.attach_message(message)

    await view.on_timeout()

    assert all(child.disabled for child in view.children)
    message.edit.assert_awaited_once_with(view=view)
