from __future__ import annotations

import logging
from pathlib import Path

import discord

from kletserbot.application.cardpacks.cardpack_service import CardpackService
from kletserbot.application.cardpacks.dto.opened_card_dto import OpenedCardDto
from kletserbot.application.cardpacks.dto.opened_pack_dto import OpenedPackDto
from kletserbot.application.cardpacks.dto.owned_pack_dto import OwnedPackDto
from kletserbot.application.exceptions import ApplicationError

_VIEW_TIMEOUT_SECONDS = 300
_CARD_BACK_FILENAME = "kletserbot-card-back.png"
_CARD_BACK_PATH = Path(__file__).with_name("assets") / _CARD_BACK_FILENAME

logger = logging.getLogger(__name__)


def build_pack_result_content(opened_pack: OpenedPackDto) -> str:
    energy_cards = tuple(card for card in opened_pack.cards if card.is_basic_energy)
    if len(energy_cards) != 1:
        raise ValueError("opened pack must contain exactly one Basic Energy")
    return (
        f"You opened a pack of: {opened_pack.set_name}. "
        f"The energy card was: {energy_cards[0].name}."
    )


def _build_card_embed(
    opened_card: OpenedCardDto,
    revealed_slot_numbers: frozenset[int],
) -> discord.Embed:
    if opened_card.is_hidden and opened_card.slot_number not in revealed_slot_numbers:
        embed = discord.Embed(
            title=f"Kaart {opened_card.slot_number} — Verborgen",
            description="🂠 Klik op de bijbehorende knop om deze kaart te onthullen.",
            colour=discord.Colour.dark_grey(),
        )
        embed.set_image(url=f"attachment://{_CARD_BACK_FILENAME}")
        return embed

    title_prefix = "✨ HIT! " if opened_card.is_hit else ""
    finish_label = {
        "normal": "Non-holo",
        "reverse_holo": "Reverse Holo",
        "holo": "Holo",
    }.get(opened_card.finish, opened_card.finish)
    embed = discord.Embed(
        title=(f"{title_prefix}Kaart {opened_card.slot_number} — {opened_card.name}"),
        description=(
            f"**Rarity:** {opened_card.rarity}\n"
            f"**Afwerking:** {finish_label}\n"
            f"**Nummer:** {opened_card.number}"
        ),
        colour=(discord.Colour.gold() if opened_card.is_hit else discord.Colour.blurple()),
    )
    embed.set_image(url=opened_card.image_url)
    return embed


class OwnerRestrictedView(discord.ui.View):
    def __init__(self, owner_user_id: int) -> None:
        super().__init__(timeout=_VIEW_TIMEOUT_SECONDS)
        self.owner_user_id = owner_user_id
        self._message: discord.Message | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.owner_user_id:
            return True
        await interaction.response.send_message(
            "Alleen de eigenaar van dit pack kan deze kaarten onthullen.",
            ephemeral=True,
        )
        return False

    def disable_all_controls(self) -> None:
        for child in self.children:
            if isinstance(child, (discord.ui.Button, discord.ui.Select)):
                child.disabled = True

    def attach_message(self, message: discord.Message) -> None:
        self._message = message

    async def on_timeout(self) -> None:
        self.disable_all_controls()
        if self._message is None:
            return
        try:
            await self._message.edit(view=self)
        except discord.HTTPException:
            logger.warning("cardpack_view_timeout_edit_failed")


class CardPageButton(discord.ui.Button["CardRevealView"]):
    def __init__(self, *, page_delta: int, disabled: bool) -> None:
        label = "Vorige" if page_delta < 0 else "Volgende"
        super().__init__(
            label=label,
            style=discord.ButtonStyle.secondary,
            disabled=disabled,
            custom_id=f"cardpack:card-page:{page_delta}",
        )
        self._page_delta = page_delta

    async def callback(self, interaction: discord.Interaction) -> None:
        if self.view is not None:
            await self.view.change_card(interaction, self._page_delta)


class CardRevealButton(discord.ui.Button["CardRevealView"]):
    def __init__(self) -> None:
        super().__init__(
            label="Onthul kaart",
            style=discord.ButtonStyle.primary,
            custom_id="cardpack:reveal-current",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if self.view is None:
            return
        await self.view.reveal_current_card(interaction)


class CardRevealView(OwnerRestrictedView):
    def __init__(
        self,
        *,
        owner_user_id: int,
        cardpack_service: CardpackService,
        opened_pack: OpenedPackDto,
    ) -> None:
        super().__init__(owner_user_id)
        self._cardpack_service = cardpack_service
        self._opened_pack = opened_pack
        self._display_cards = tuple(card for card in opened_pack.cards if not card.is_basic_energy)
        if not self._display_cards:
            raise ValueError("opened pack requires at least one display card")
        self._current_card_index = 0
        self._revealed_slot_numbers: set[int] = set()
        self._rebuild_controls()

    @property
    def display_cards(self) -> tuple[OpenedCardDto, ...]:
        return self._display_cards

    @property
    def current_card(self) -> OpenedCardDto:
        return self._display_cards[self._current_card_index]

    @property
    def current_card_index(self) -> int:
        return self._current_card_index

    @property
    def current_embed(self) -> discord.Embed:
        embed = _build_card_embed(
            self.current_card,
            frozenset(self._revealed_slot_numbers),
        )
        embed.set_footer(text=f"Kaart {self._current_card_index + 1}/{len(self._display_cards)}")
        return embed

    def current_attachments(self) -> list[discord.File]:
        if (
            self.current_card.is_hidden
            and self.current_card.slot_number not in self._revealed_slot_numbers
        ):
            return [
                discord.File(
                    _CARD_BACK_PATH,
                    filename=_CARD_BACK_FILENAME,
                )
            ]
        return []

    @property
    def revealed_slot_numbers(self) -> frozenset[int]:
        return frozenset(self._revealed_slot_numbers)

    async def change_card(
        self,
        interaction: discord.Interaction,
        page_delta: int,
    ) -> None:
        new_index = self._current_card_index + page_delta
        cannot_advance = (
            page_delta > 0
            and self.current_card.is_hidden
            and self.current_card.slot_number not in self._revealed_slot_numbers
        )
        if cannot_advance or not 0 <= new_index < len(self._display_cards):
            await interaction.response.send_message(
                "Onthul deze kaart voordat je verdergaat.",
                ephemeral=True,
            )
            return
        self._current_card_index = new_index
        self._rebuild_controls()
        await interaction.response.edit_message(
            embed=self.current_embed,
            attachments=self.current_attachments(),
            view=self,
        )

    async def reveal_current_card(
        self,
        interaction: discord.Interaction,
    ) -> None:
        current_card = self.current_card
        if not current_card.is_hidden or current_card.slot_number in self._revealed_slot_numbers:
            await interaction.response.send_message(
                "Deze kaart kan niet opnieuw worden onthuld.",
                ephemeral=True,
            )
            return

        self._revealed_slot_numbers.add(current_card.slot_number)
        self._rebuild_controls()
        hidden_slot_numbers = {card.slot_number for card in self._display_cards if card.is_hidden}
        if self._revealed_slot_numbers == hidden_slot_numbers:
            await self._add_open_another_pack_control()
        await interaction.response.edit_message(
            embed=self.current_embed,
            attachments=self.current_attachments(),
            view=self,
        )

    async def open_another_pack(self, interaction: discord.Interaction) -> None:
        self.disable_all_controls()
        await _open_pack_into_message(
            interaction=interaction,
            owner_user_id=self.owner_user_id,
            cardpack_service=self._cardpack_service,
            set_id=self._opened_pack.set_id,
        )

    async def _add_open_another_pack_control(self) -> None:
        try:
            inventory = await self._cardpack_service.retrieve_inventory(self.owner_user_id)
        except ApplicationError:
            logger.warning(
                "cardpack_remaining_inventory_unavailable set_id=%s",
                self._opened_pack.set_id,
            )
            return
        if any(
            owned_pack.set_id == self._opened_pack.set_id and owned_pack.quantity > 0
            for owned_pack in inventory
        ):
            self.add_item(OpenAnotherPackButton())

    def _rebuild_controls(self) -> None:
        self.clear_items()
        self.add_item(
            CardPageButton(
                page_delta=-1,
                disabled=self._current_card_index == 0,
            )
        )
        current_is_unrevealed = (
            self.current_card.is_hidden
            and self.current_card.slot_number not in self._revealed_slot_numbers
        )
        if current_is_unrevealed:
            self.add_item(CardRevealButton())
        self.add_item(
            CardPageButton(
                page_delta=1,
                disabled=(
                    self._current_card_index == len(self._display_cards) - 1
                    or current_is_unrevealed
                ),
            )
        )


class OpenAnotherPackButton(discord.ui.Button[CardRevealView]):
    def __init__(self) -> None:
        super().__init__(
            label="Open another pack",
            emoji="✨",
            style=discord.ButtonStyle.success,
            custom_id="cardpack:open-another",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if self.view is not None:
            await self.view.open_another_pack(interaction)


class InventoryPageButton(discord.ui.Button["InventorySelectionView"]):
    def __init__(self, *, page_delta: int, disabled: bool) -> None:
        label = "Vorige" if page_delta < 0 else "Volgende"
        super().__init__(
            label=label,
            style=discord.ButtonStyle.secondary,
            disabled=disabled,
            custom_id=f"cardpack:inventory-page:{page_delta}",
        )
        self._page_delta = page_delta

    async def callback(self, interaction: discord.Interaction) -> None:
        if self.view is not None:
            await self.view.change_page(interaction, self._page_delta)


class InventoryOpenPackButton(discord.ui.Button["InventorySelectionView"]):
    def __init__(self, set_id: str) -> None:
        super().__init__(
            label="Open pack",
            emoji="✨",
            style=discord.ButtonStyle.success,
            custom_id=f"cardpack:open:{set_id}",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if self.view is not None:
            await self.view.open_current_pack(interaction)


class InventorySelectionView(OwnerRestrictedView):
    def __init__(
        self,
        *,
        owner_user_id: int,
        cardpack_service: CardpackService,
        owned_packs: tuple[OwnedPackDto, ...],
    ) -> None:
        super().__init__(owner_user_id)
        if not owned_packs:
            raise ValueError("inventory selection requires at least one pack")
        self._cardpack_service = cardpack_service
        self._owned_packs = owned_packs
        self._page_index = 0
        self._rebuild_controls()

    @property
    def page_count(self) -> int:
        return len(self._owned_packs)

    @property
    def embed(self) -> discord.Embed:
        owned_pack = self._current_pack
        embed = discord.Embed(
            title=owned_pack.set_name,
            description=f"Je hebt nog **{owned_pack.quantity}** pack(s).",
            colour=discord.Colour.blurple(),
        )
        embed.set_image(url=f"attachment://{owned_pack.pack_image_asset}")
        if self.page_count > 1:
            embed.set_footer(text=f"Pack {self._page_index + 1}/{self.page_count}")
        return embed

    @property
    def pack_image_file(self) -> discord.File:
        asset_name = self._current_pack.pack_image_asset
        return discord.File(
            _CARD_BACK_PATH.parent / asset_name,
            filename=asset_name,
        )

    def pack_image_attachments(self) -> list[discord.File]:
        return [self.pack_image_file]

    async def change_page(
        self,
        interaction: discord.Interaction,
        page_delta: int,
    ) -> None:
        new_page_index = self._page_index + page_delta
        if not 0 <= new_page_index < self.page_count:
            await interaction.response.send_message(
                "Die inventarispagina bestaat niet.",
                ephemeral=True,
            )
            return
        self._page_index = new_page_index
        self._rebuild_controls()
        await interaction.response.edit_message(
            content=None,
            embed=self.embed,
            attachments=self.pack_image_attachments(),
            view=self,
        )

    async def open_current_pack(
        self,
        interaction: discord.Interaction,
    ) -> None:
        self.disable_all_controls()
        await _open_pack_into_message(
            interaction=interaction,
            owner_user_id=self.owner_user_id,
            cardpack_service=self._cardpack_service,
            set_id=self._current_pack.set_id,
        )

    @property
    def _current_pack(self) -> OwnedPackDto:
        return self._owned_packs[self._page_index]

    def _rebuild_controls(self) -> None:
        self.clear_items()
        self.add_item(InventoryOpenPackButton(self._current_pack.set_id))
        if self.page_count > 1:
            self.add_item(
                InventoryPageButton(
                    page_delta=-1,
                    disabled=self._page_index == 0,
                )
            )
            self.add_item(
                InventoryPageButton(
                    page_delta=1,
                    disabled=self._page_index == self.page_count - 1,
                )
            )


async def _open_pack_into_message(
    *,
    interaction: discord.Interaction,
    owner_user_id: int,
    cardpack_service: CardpackService,
    set_id: str,
) -> None:
    await interaction.response.defer()
    try:
        opened_pack = await cardpack_service.open_pack(
            discord_user_id=owner_user_id,
            set_id=set_id,
        )
    except ApplicationError:
        await interaction.followup.send(
            "Dit pack kon niet worden geopend. Controleer je inventaris en probeer opnieuw.",
            ephemeral=True,
        )
        return

    reveal_view = CardRevealView(
        owner_user_id=owner_user_id,
        cardpack_service=cardpack_service,
        opened_pack=opened_pack,
    )
    primary_message = await interaction.edit_original_response(
        content=build_pack_result_content(opened_pack),
        embed=reveal_view.current_embed,
        attachments=reveal_view.current_attachments(),
        view=reveal_view,
    )
    reveal_view.attach_message(primary_message)
