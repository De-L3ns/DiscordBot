import datetime
import logging
from zoneinfo import ZoneInfo

import discord
from discord.ext import commands, tasks

from kletserbot.apps.general.application.birthdays.birthday_service import BirthdayService

logger = logging.getLogger(__name__)


class BirthdayCog(commands.Cog):
    def __init__(
        self,
        *,
        bot: commands.Bot,
        birthday_service: BirthdayService,
        birthday_channel_id: int,
        timezone: ZoneInfo,
    ) -> None:
        self._bot = bot
        self._birthday_service = birthday_service
        self._birthday_channel_id = birthday_channel_id
        self._timezone = timezone
        self.birthday_loop.change_interval(time=datetime.time(hour=12, tzinfo=timezone))

    async def cog_load(self) -> None:
        self.birthday_loop.start()

    async def cog_unload(self) -> None:
        self.birthday_loop.cancel()

    @tasks.loop(time=datetime.time(hour=12, tzinfo=datetime.UTC))
    async def birthday_loop(self) -> None:
        current_date = datetime.datetime.now(self._timezone).date()
        announcements = self._birthday_service.find_announcements(current_date)
        if not announcements:
            return

        channel = self._bot.get_channel(self._birthday_channel_id)
        if channel is None:
            try:
                channel = await self._bot.fetch_channel(self._birthday_channel_id)
            except discord.DiscordException:
                logger.exception(
                    "birthday_channel_unavailable",
                    extra={"channel_id": self._birthday_channel_id},
                )
                return

        for announcement in announcements:
            try:
                await channel.send(  # type: ignore[union-attr]
                    f"@everyone {announcement.announcement_text}"
                )
            except discord.DiscordException:
                logger.exception(
                    "birthday_announcement_failed",
                    extra={"channel_id": self._birthday_channel_id},
                )

    @birthday_loop.before_loop
    async def wait_until_ready(self) -> None:
        await self._bot.wait_until_ready()
