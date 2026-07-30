import logging

import discord
from discord import app_commands
from discord.ext import commands

from kletserbot.application.cardpacks.cardpack_service import CardpackService
from kletserbot.application.exceptions import ApplicationError
from kletserbot.presentation.discord.cardpack_views import InventorySelectionView

logger = logging.getLogger(__name__)


class CardpacksCog(commands.Cog):
    def __init__(self, cardpack_service: CardpackService) -> None:
        self._cardpack_service = cardpack_service

    async def cog_load(self) -> None:
        try:
            await self._cardpack_service.initialize()
        except ApplicationError:
            logger.exception("cardpack_initialization_failed")
        except Exception:
            logger.exception("cardpack_initialization_unexpected_failure")

    @app_commands.command(
        name="pack",
        description="Bekijk en open je ongeopende Pokémonpacks.",
    )
    async def pack(self, interaction: discord.Interaction) -> None:
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
