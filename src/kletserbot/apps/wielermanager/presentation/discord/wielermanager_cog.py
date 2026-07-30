import logging

import discord
from discord import app_commands
from discord.ext import commands, tasks

from kletserbot.apps.wielermanager.application.wielermanager_service import (
    WielermanagerService,
)
from kletserbot.apps.wielermanager.presentation.discord.response_formatter import (
    format_cycling_leaderboard,
)
from kletserbot.shared.application.exceptions import ApplicationError

logger = logging.getLogger(__name__)


class WielermanagerCog(commands.Cog):
    def __init__(
        self,
        *,
        bot: commands.Bot,
        wielermanager_service: WielermanagerService,
        is_polling_enabled: bool,
        polling_channel_id: int | None,
        polling_interval_minutes: int,
    ) -> None:
        self._bot = bot
        self._wielermanager_service = wielermanager_service
        self._is_polling_enabled = is_polling_enabled
        self._polling_channel_id = polling_channel_id
        self.polling_loop.change_interval(minutes=polling_interval_minutes)

    async def cog_load(self) -> None:
        if self._is_polling_enabled:
            self.polling_loop.start()

    async def cog_unload(self) -> None:
        self.polling_loop.cancel()

    @app_commands.command(
        name="wielermanager",
        description="Toon het huidige Sporza Wielermanager-klassement.",
    )
    async def wielermanager(
        self,
        interaction: discord.Interaction,
    ) -> None:
        await interaction.response.defer()
        try:
            leaderboard = await self._wielermanager_service.retrieve_leaderboard()
            await interaction.followup.send(format_cycling_leaderboard(leaderboard))
        except ApplicationError:
            logger.exception("wielermanager_command_failed")
            await interaction.followup.send(
                "Ik kon het Wielermanager-klassement niet ophalen.",
                ephemeral=True,
            )
        except Exception:
            logger.exception("wielermanager_command_unexpected_failure")
            await interaction.followup.send(
                "Er ging onverwacht iets mis.",
                ephemeral=True,
            )

    @tasks.loop(minutes=15)
    async def polling_loop(self) -> None:
        if self._polling_channel_id is None:
            return
        try:
            leaderboard = await self._wielermanager_service.poll_for_movements()
        except ApplicationError:
            logger.exception("wielermanager_poll_failed")
            return
        except Exception:
            logger.exception("wielermanager_poll_unexpected_failure")
            return
        if leaderboard is None:
            return

        channel = self._bot.get_channel(self._polling_channel_id)
        if channel is None:
            try:
                channel = await self._bot.fetch_channel(self._polling_channel_id)
            except discord.DiscordException:
                logger.exception(
                    "wielermanager_channel_unavailable",
                    extra={"channel_id": self._polling_channel_id},
                )
                return
        try:
            await channel.send(  # type: ignore[union-attr]
                format_cycling_leaderboard(leaderboard)
            )
        except discord.DiscordException:
            logger.exception(
                "wielermanager_alert_failed",
                extra={"channel_id": self._polling_channel_id},
            )

    @polling_loop.before_loop
    async def wait_until_ready(self) -> None:
        await self._bot.wait_until_ready()
