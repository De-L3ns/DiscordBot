import asyncio
import logging

import discord
from discord import app_commands
from discord.ext import commands

from kletserbot.apps.cardpacks.application.cardpack_service import CardpackService
from kletserbot.apps.cardpacks.application.dto.opened_card_dto import OpenedCardDto
from kletserbot.apps.cardpacks.presentation.discord.cardpack_views import (
    CollectionSelectionView,
    InventorySelectionView,
)
from kletserbot.shared.application.exceptions import ApplicationError

logger = logging.getLogger(__name__)


class CardpacksCog(commands.Cog):
    def __init__(
        self,
        cardpack_service: CardpackService,
        *,
        bot: commands.Bot | None = None,
        hit_channel_id: int | None = None,
    ) -> None:
        self._cardpack_service = cardpack_service
        self._bot = bot
        self._hit_channel_id = hit_channel_id

    async def cog_load(self) -> None:
        try:
            await self._cardpack_service.initialize()
        except ApplicationError:
            logger.exception("cardpack_initialization_failed")
        except Exception:
            logger.exception("cardpack_initialization_unexpected_failure")

    @app_commands.command(
        name="packs",
        description="Bekijk en open je ongeopende Pokémonpacks.",
    )
    async def packs(self, interaction: discord.Interaction) -> None:
        try:
            owned_packs = await self._cardpack_service.retrieve_inventory(interaction.user.id)
            if not owned_packs:
                await interaction.response.send_message(
                    "Je hebt momenteel geen ongeopende Pokémonpacks.",
                    ephemeral=True,
                )
                return
            view = InventorySelectionView(
                owner_user_id=interaction.user.id,
                cardpack_service=self._cardpack_service,
                owned_packs=owned_packs,
                on_hit_revealed=self._announce_hit,
            )
            await interaction.response.send_message(
                embed=view.embed,
                files=view.pack_image_attachments(),
                view=view,
                ephemeral=True,
            )
            view.attach_message(await interaction.original_response())
        except ApplicationError:
            logger.exception("pack_inventory_command_failed")
            await interaction.response.send_message(
                "Je packinventaris kon momenteel niet worden opgehaald.",
                ephemeral=True,
            )
        except Exception:
            logger.exception("pack_inventory_command_unexpected_failure")
            await interaction.response.send_message(
                "Er ging onverwacht iets mis.",
                ephemeral=True,
            )

    async def _announce_hit(
        self,
        discord_user_id: int,
        set_id: str,
        card: OpenedCardDto,
    ) -> None:
        if self._bot is None or self._hit_channel_id is None:
            return
        channel = self._bot.get_channel(self._hit_channel_id)
        if channel is None:
            try:
                channel = await self._bot.fetch_channel(self._hit_channel_id)
            except discord.DiscordException:
                logger.exception(
                    "cardpack_hit_channel_unavailable",
                    extra={"channel_id": self._hit_channel_id},
                )
                return
        try:
            quantity, collection_set = await self._retrieve_hit_collection_details(
                discord_user_id,
                set_id,
                card.card_id,
            )
        except ApplicationError:
            logger.exception(
                "cardpack_hit_collection_details_unavailable",
                extra={"card_id": card.card_id, "set_id": set_id},
            )
            quantity, collection_set = 0, None

        embed = discord.Embed(
            title="✨ Er werd een nieuwe hit gepulled!",
            description=f"<@{discord_user_id}> heeft **{card.name}** gepulled!",
            colour=discord.Colour.gold(),
        )
        embed.add_field(name="Rarity", value=card.rarity, inline=True)
        embed.add_field(name="Aantal exemplaren", value=f"{quantity}×", inline=True)
        if collection_set is not None:
            set_name, collected_cards, total_cards = collection_set
            completion = 100 * collected_cards / total_cards if total_cards else 0
            embed.add_field(
                name=set_name,
                value=f"Voltooid: {collected_cards}/{total_cards} ({completion:.1f}%)",
                inline=False,
            )
        embed.set_image(url=card.image_url)
        try:
            await channel.send(embed=embed)  # type: ignore[union-attr]
        except discord.DiscordException:
            logger.exception(
                "cardpack_hit_announcement_failed",
                extra={"channel_id": self._hit_channel_id, "card_id": card.card_id},
            )

    async def _retrieve_hit_collection_details(
        self,
        discord_user_id: int,
        set_id: str,
        card_id: str,
    ) -> tuple[int, tuple[str, int, int] | None]:
        album_cards, collection_sets = await asyncio.gather(
            self._cardpack_service.retrieve_album_cards(discord_user_id, set_id),
            self._cardpack_service.retrieve_collection_sets(discord_user_id),
        )
        quantity = next(
            (album_card.quantity for album_card in album_cards if album_card.card_id == card_id),
            0,
        )
        collection_set = next(
            (summary for summary in collection_sets if summary.set_id == set_id),
            None,
        )
        if collection_set is None:
            return quantity, None
        return quantity, (
            collection_set.set_name,
            collection_set.collected_cards,
            collection_set.total_cards,
        )

    @app_commands.command(
        name="collection",
        description="Bekijk een Pokémon-kaartencollectie.",
    )
    @app_commands.describe(user="De gebruiker wiens collectie je wilt bekijken.")
    async def collection(
        self,
        interaction: discord.Interaction,
        user: discord.Member | None = None,
    ) -> None:
        collection_user = user or interaction.user
        try:
            sets = await self._cardpack_service.retrieve_collection_sets(collection_user.id)
            if not sets:
                await interaction.response.send_message(
                    "Deze gebruiker heeft nog geen kaarten in de collectie.",
                    ephemeral=True,
                )
                return
            view = CollectionSelectionView(
                owner_user_id=interaction.user.id,
                collection_user_id=collection_user.id,
                cardpack_service=self._cardpack_service,
                sets=sets,
            )
            await interaction.response.send_message(embed=view.embed, view=view, ephemeral=True)
            view.attach_message(await interaction.original_response())
        except ApplicationError:
            logger.exception("cardpack_collection_command_failed")
            await interaction.response.send_message(
                "De collectie kon momenteel niet worden opgehaald.", ephemeral=True
            )
        except Exception:
            logger.exception("cardpack_collection_command_unexpected_failure")
            await interaction.response.send_message("Er ging onverwacht iets mis.", ephemeral=True)

    @app_commands.command(
        name="giftpack",
        description="Geef ongeopende Pokémonpacks cadeau.",
    )
    @app_commands.default_permissions(administrator=True)
    @app_commands.describe(
        user="De gebruiker die packs ontvangt.",
        set_id="De Pokémonset.",
        amount="Het aantal packs (1–100).",
    )
    async def giftpack(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        set_id: str,
        amount: app_commands.Range[int, 1, 100],
    ) -> None:
        if not interaction.permissions.administrator:
            await interaction.response.send_message(
                "Je hebt beheerdersrechten nodig voor dit commando.",
                ephemeral=True,
            )
            return
        try:
            await self._cardpack_service.gift_packs(user.id, set_id, amount)
            available_set = next(
                card_set
                for card_set in self._cardpack_service.retrieve_available_sets()
                if card_set.set_id == set_id
            )
            await interaction.response.send_message(
                f"🎁 {user.mention} kreeg {amount} × {available_set.set_name}.",
                ephemeral=True,
            )
        except ApplicationError:
            logger.exception("giftpack_command_failed")
            await interaction.response.send_message(
                "Dit pack kon niet worden geschonken. Controleer de set en het aantal.",
                ephemeral=True,
            )
        except Exception:
            logger.exception("giftpack_command_unexpected_failure")
            await interaction.response.send_message(
                "Er ging onverwacht iets mis.",
                ephemeral=True,
            )

    @giftpack.autocomplete("set_id")
    async def giftpack_set_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        del interaction
        normalized_current = current.casefold()
        return [
            app_commands.Choice(name=card_set.set_name, value=card_set.set_id)
            for card_set in self._cardpack_service.retrieve_available_sets()
            if normalized_current in card_set.set_name.casefold()
            or normalized_current in card_set.set_id.casefold()
        ][:25]
