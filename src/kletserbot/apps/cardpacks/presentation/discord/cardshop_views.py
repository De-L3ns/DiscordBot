from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

import discord

from kletserbot.apps.cardpacks.application.cardpack_service import CardpackService
from kletserbot.apps.cardpacks.application.dto.available_card_set_dto import (
    AvailableCardSetDto,
)
from kletserbot.apps.cardpacks.application.dto.cardshop_dto import (
    CardshopDto,
    CardshopProductDto,
)
from kletserbot.apps.cardpacks.application.exceptions import InsufficientPointsError
from kletserbot.shared.application.exceptions import ApplicationError

logger = logging.getLogger(__name__)

_PRIVATE_VIEW_TIMEOUT_SECONDS = 300
_PRODUCTS_PER_PAGE = 25
_CARDPACK_APP_ROOT = Path(__file__).parents[2]
_ASSET_DIRECTORY = _CARDPACK_APP_ROOT / "assets" / "discord"
_SHOP_PACK_IMAGE_ASSETS = {
    "card-pack-image-151.webp": "card-pack-image-151-shop-thumbnail.png",
    "card-pack-image-baseset.jpg": "card-pack-image-baseset-shop-thumbnail.png",
}


class CardshopLaunchView(discord.ui.LayoutView):
    def __init__(
        self,
        cardpack_service: CardpackService,
        *,
        available_sets: tuple[AvailableCardSetDto, ...] = (),
    ) -> None:
        super().__init__(timeout=None)
        self._cardpack_service = cardpack_service
        self._available_sets = available_sets
        self.add_item(
            discord.ui.TextDisplay(
                "# Pokemon Pack shop\n"
                "Hieronder kan je alle packs vinden die momenteel kunnen worden gekocht. "
                "Klik op de knop 'Packs kopen' om je huidig saldo te zien en te "
                "selecteren welke pack(s) je wilt kopen. Klik op Claim daily om je "
                "dagelijkse punten te krijgen."
            )
        )
        for card_set in available_sets[:5]:
            shop_image_asset = _shop_pack_image_asset(card_set.pack_image_asset)
            self.add_item(
                discord.ui.Container(
                    discord.ui.Section(
                        f"**{card_set.set_name}**\n"
                        f"{card_set.shop_description}\n"
                        f"**{card_set.shop_price:,} punten**",
                        accessory=discord.ui.Thumbnail(
                            f"attachment://{shop_image_asset}",
                            description=f"{card_set.set_name} pack",
                        ),
                    ),
                    accent_colour=discord.Colour.blurple(),
                )
            )
        action_row: discord.ui.ActionRow[CardshopLaunchView] = discord.ui.ActionRow()
        action_row.add_item(OpenPrivateShopButton())
        action_row.add_item(ClaimDailyPointsButton())
        self.add_item(action_row)

    def pack_image_files(self) -> list[discord.File]:
        selected_assets: set[str] = set()
        files: list[discord.File] = []
        for card_set in self._available_sets[:5]:
            shop_image_asset = _shop_pack_image_asset(card_set.pack_image_asset)
            if shop_image_asset in selected_assets:
                continue
            selected_assets.add(shop_image_asset)
            files.append(
                discord.File(
                    _ASSET_DIRECTORY / shop_image_asset,
                    filename=shop_image_asset,
                )
            )
        return files

    async def open_private_shop(self, interaction: discord.Interaction) -> None:
        try:
            cardshop = await self._cardpack_service.retrieve_cardshop(interaction.user.id)
            await interaction.response.send_message(
                view=CardshopPrivateView(
                    owner_user_id=interaction.user.id,
                    cardpack_service=self._cardpack_service,
                    cardshop=cardshop,
                ),
                ephemeral=True,
            )
        except ApplicationError:
            logger.exception("cardshop_open_failed")
            await interaction.response.send_message(
                "Je privéshop kon momenteel niet worden geopend.", ephemeral=True
            )

    async def claim_daily_points(self, interaction: discord.Interaction) -> None:
        try:
            claim = await self._cardpack_service.claim_daily_points(interaction.user.id)
            cardshop = await self._cardpack_service.retrieve_cardshop(interaction.user.id)
            notice = (
                f"Je dagelijkse {claim.awarded_points:,} punten zijn toegevoegd."
                if claim.was_claimed
                else (
                    "Je hebt je dagelijkse punten vandaag al opgehaald. "
                    "Je kunt opnieuw punten claimen "
                    f"{_discord_timestamp(claim.next_claim_at_utc)}."
                )
            )
            await interaction.response.send_message(
                view=CardshopPrivateView(
                    owner_user_id=interaction.user.id,
                    cardpack_service=self._cardpack_service,
                    cardshop=cardshop,
                    notice=notice,
                ),
                ephemeral=True,
            )
        except ApplicationError:
            logger.exception("cardshop_daily_claim_failed")
            await interaction.response.send_message(
                "Je dagelijkse punten konden momenteel niet worden opgehaald.",
                ephemeral=True,
            )


class OpenPrivateShopButton(discord.ui.Button[CardshopLaunchView]):
    def __init__(self) -> None:
        super().__init__(
            label="Packs kopen",
            style=discord.ButtonStyle.primary,
            custom_id="cardshop:open",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if self.view is not None:
            await self.view.open_private_shop(interaction)


class ClaimDailyPointsButton(discord.ui.Button[CardshopLaunchView]):
    def __init__(self) -> None:
        super().__init__(
            label="Claim daily",
            style=discord.ButtonStyle.secondary,
            custom_id="cardshop:daily",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if self.view is not None:
            await self.view.claim_daily_points(interaction)


class CardshopPrivateView(discord.ui.LayoutView):
    def __init__(
        self,
        *,
        owner_user_id: int,
        cardpack_service: CardpackService,
        cardshop: CardshopDto,
        notice: str | None = None,
    ) -> None:
        super().__init__(timeout=_PRIVATE_VIEW_TIMEOUT_SECONDS)
        if not cardshop.products:
            raise ValueError("private cardshop requires at least one product")
        self.owner_user_id = owner_user_id
        self._cardpack_service = cardpack_service
        self._cardshop = cardshop
        self._notice = notice
        self._selected_product_index = 0
        self._product_page_index = 0
        self._quantity = 1
        self._rebuild_components()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.owner_user_id:
            return True
        await interaction.response.send_message(
            "Deze privéshop is alleen zichtbaar voor de gebruiker die hem opende.",
            ephemeral=True,
        )
        return False

    async def select_product(self, interaction: discord.Interaction, set_id: str) -> None:
        selected_index = next(
            (
                index
                for index, product in enumerate(self._cardshop.products)
                if product.set_id == set_id
            ),
            None,
        )
        if selected_index is None:
            await interaction.response.send_message(
                "Dit pack is momenteel niet beschikbaar.", ephemeral=True
            )
            return
        self._selected_product_index = selected_index
        self._product_page_index = selected_index // _PRODUCTS_PER_PAGE
        self._notice = None
        self._rebuild_components()
        await interaction.response.edit_message(view=self)

    async def change_quantity(self, interaction: discord.Interaction, delta: int) -> None:
        self._quantity = min(10, max(1, self._quantity + delta))
        self._notice = None
        self._rebuild_components()
        await interaction.response.edit_message(view=self)

    async def change_product_page(self, interaction: discord.Interaction, delta: int) -> None:
        new_page_index = self._product_page_index + delta
        if not 0 <= new_page_index < self._product_page_count:
            await interaction.response.send_message(
                "Deze shop-pagina bestaat niet.", ephemeral=True
            )
            return
        self._product_page_index = new_page_index
        self._notice = None
        self._rebuild_components()
        await interaction.response.edit_message(view=self)

    async def purchase(self, interaction: discord.Interaction) -> None:
        try:
            purchase = await self._cardpack_service.purchase_packs(
                self.owner_user_id,
                self._selected_product.set_id,
                self._quantity,
            )
            self._cardshop = await self._cardpack_service.retrieve_cardshop(self.owner_user_id)
            self._selected_product_index = next(
                index
                for index, product in enumerate(self._cardshop.products)
                if product.set_id == purchase.set_id
            )
            self._product_page_index = self._selected_product_index // _PRODUCTS_PER_PAGE
            self._notice = (
                f"Succes! {purchase.quantity} × {purchase.set_name} is toegevoegd "
                "aan je inventaris."
            )
        except InsufficientPointsError:
            total_price = self._selected_product.price * self._quantity
            shortfall = max(0, total_price - self._cardshop.point_balance)
            self._notice = f"Je hebt nog {shortfall:,} punten nodig voor deze aankoop."
        except ApplicationError:
            logger.exception("cardshop_purchase_failed")
            self._notice = "Deze aankoop kon momenteel niet worden voltooid."
        self._rebuild_components()
        await interaction.response.edit_message(view=self)

    @property
    def _selected_product(self) -> CardshopProductDto:
        return self._cardshop.products[self._selected_product_index]

    @property
    def _product_page_count(self) -> int:
        return (len(self._cardshop.products) + _PRODUCTS_PER_PAGE - 1) // _PRODUCTS_PER_PAGE

    @property
    def _current_page_products(self) -> tuple[CardshopProductDto, ...]:
        first_product_index = self._product_page_index * _PRODUCTS_PER_PAGE
        return self._cardshop.products[
            first_product_index : first_product_index + _PRODUCTS_PER_PAGE
        ]

    def _rebuild_components(self) -> None:
        selected_product = self._selected_product
        total_price = selected_product.price * self._quantity
        owned_pack_summary = "\n".join(
            f"• **{product.set_name}:** {product.owned_quantity} pack(s)"
            for product in self._cardshop.products
        )
        self.clear_items()
        notice = f"\n\n{self._notice}" if self._notice else ""
        self.add_item(
            discord.ui.TextDisplay(
                "# Packs kopen\n"
                f"**Jouw saldo:** {self._cardshop.point_balance:,} punten\n"
                f"**Geselecteerd:** {self._quantity} × {selected_product.set_name}\n"
                f"**Omschrijving:** {selected_product.description}\n"
                f"**Totaal:** {total_price:,} punten\n\n"
                f"**Jouw packs:**\n{owned_pack_summary}{notice}"
            )
        )
        product_row: discord.ui.ActionRow[CardshopPrivateView] = discord.ui.ActionRow()
        product_row.add_item(
            CardshopProductSelect(self._current_page_products, selected_product.set_id)
        )
        self.add_item(product_row)
        if self._product_page_count > 1:
            page_row: discord.ui.ActionRow[CardshopPrivateView] = discord.ui.ActionRow()
            page_row.add_item(
                CardshopProductPageButton(
                    delta=-1,
                    disabled=self._product_page_index == 0,
                )
            )
            page_row.add_item(
                CardshopProductPageButton(
                    delta=1,
                    disabled=self._product_page_index == self._product_page_count - 1,
                )
            )
            self.add_item(page_row)
        purchase_row: discord.ui.ActionRow[CardshopPrivateView] = discord.ui.ActionRow()
        purchase_row.add_item(CardshopQuantityButton(delta=-1))
        purchase_row.add_item(CardshopQuantityButton(delta=1))
        purchase_row.add_item(CardshopPurchaseButton())
        self.add_item(purchase_row)


class CardshopProductSelect(discord.ui.Select[CardshopPrivateView]):
    def __init__(
        self,
        products: tuple[CardshopProductDto, ...],
        selected_set_id: str,
    ) -> None:
        super().__init__(
            custom_id="cardshop:select-product",
            placeholder="Kies een Pokémonset",
            options=[
                discord.SelectOption(
                    label=product.set_name[:100],
                    value=product.set_id,
                    description=(
                        f"{product.price:,} punten - {product.owned_quantity} pack(s) in bezit"
                    )[:100],
                    default=product.set_id == selected_set_id,
                )
                for product in products
            ],
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if self.view is not None:
            await self.view.select_product(interaction, self.values[0])


class CardshopProductPageButton(discord.ui.Button[CardshopPrivateView]):
    def __init__(self, *, delta: int, disabled: bool) -> None:
        super().__init__(
            label="Vorige sets" if delta < 0 else "Volgende sets",
            style=discord.ButtonStyle.secondary,
            custom_id=f"cardshop:product-page:{delta}",
            disabled=disabled,
        )
        self._delta = delta

    async def callback(self, interaction: discord.Interaction) -> None:
        if self.view is not None:
            await self.view.change_product_page(interaction, self._delta)


class CardshopQuantityButton(discord.ui.Button[CardshopPrivateView]):
    def __init__(self, *, delta: int) -> None:
        super().__init__(
            label="−" if delta < 0 else "+",
            style=discord.ButtonStyle.secondary,
            custom_id=f"cardshop:quantity:{delta}",
        )
        self._delta = delta

    async def callback(self, interaction: discord.Interaction) -> None:
        if self.view is not None:
            await self.view.change_quantity(interaction, self._delta)


class CardshopPurchaseButton(discord.ui.Button[CardshopPrivateView]):
    def __init__(self) -> None:
        super().__init__(
            label="Packs kopen",
            style=discord.ButtonStyle.success,
            custom_id="cardshop:purchase",
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if self.view is not None:
            await self.view.purchase(interaction)


def _discord_timestamp(value: datetime) -> str:
    return f"<t:{int(value.timestamp())}:R>"


def _shop_pack_image_asset(pack_image_asset: str) -> str:
    return _SHOP_PACK_IMAGE_ASSETS.get(pack_image_asset, pack_image_asset)
