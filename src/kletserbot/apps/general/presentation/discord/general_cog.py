import logging

import discord
from discord import app_commands
from discord.ext import commands

from kletserbot.apps.general.application.nostalgia.nostalgia_service import NostalgiaService
from kletserbot.apps.general.application.quotes.quote_service import QuoteService
from kletserbot.shared.application.exceptions import ApplicationError

logger = logging.getLogger(__name__)


class GeneralCog(commands.Cog):
    def __init__(
        self,
        quote_service: QuoteService,
        nostalgia_service: NostalgiaService,
    ) -> None:
        self._quote_service = quote_service
        self._nostalgia_service = nostalgia_service

    @app_commands.command(
        name="citaat",
        description="Post een willekeurig citaat.",
    )
    async def citaat(self, interaction: discord.Interaction) -> None:
        try:
            quote = self._quote_service.retrieve_quote()
            await interaction.response.send_message(f"*{quote.text}*")
        except ApplicationError:
            logger.exception("quote_command_failed")
            await interaction.response.send_message(
                "Ik kon momenteel geen citaat kiezen.",
                ephemeral=True,
            )
        except Exception:
            logger.exception("quote_command_unexpected_failure")
            await interaction.response.send_message(
                "Er ging onverwacht iets mis.",
                ephemeral=True,
            )

    @app_commands.command(
        name="nostalgie",
        description="Post een willekeurige foto uit de oude doos.",
    )
    async def nostalgie(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        try:
            image = await self._nostalgia_service.retrieve_image()
            embed = discord.Embed(title=image.title)
            embed.set_image(url=image.image_url)
            await interaction.followup.send(embed=embed)
        except ApplicationError:
            logger.exception("nostalgia_command_failed")
            await interaction.followup.send(
                "Ik kon momenteel geen nostalgiefoto ophalen.",
                ephemeral=True,
            )
        except Exception:
            logger.exception("nostalgia_command_unexpected_failure")
            await interaction.followup.send(
                "Er ging onverwacht iets mis.",
                ephemeral=True,
            )
