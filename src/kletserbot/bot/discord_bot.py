import logging
from collections.abc import Sequence
from pathlib import Path

import discord
from discord.ext import commands

_LOGGER = logging.getLogger(__name__)
_DEFAULT_READINESS_MARKER_PATH = Path("/tmp/kletserbot-ready")


class KletserBot(commands.Bot):
    def __init__(
        self,
        *,
        cogs: Sequence[commands.Cog],
        development_guild_id: int | None,
        readiness_marker_path: Path = _DEFAULT_READINESS_MARKER_PATH,
    ) -> None:
        intents = discord.Intents.none()
        intents.guilds = True
        intents.reactions = True
        super().__init__(
            command_prefix=commands.when_mentioned,
            intents=intents,
            help_command=None,
        )
        self._pending_cogs = tuple(cogs)
        self._development_guild_id = development_guild_id
        self._readiness_marker_path = readiness_marker_path
        self._are_cogs_installed = False
        self._remove_readiness_marker()

    async def setup_hook(self) -> None:
        if not self._are_cogs_installed:
            for cog in self._pending_cogs:
                await self.add_cog(cog)
            self._are_cogs_installed = True

        if self._development_guild_id is None:
            await self.tree.sync()
            return

        development_guild = discord.Object(id=self._development_guild_id)
        self.tree.copy_global_to(guild=development_guild)
        await self.tree.sync(guild=development_guild)
        # Development commands are guild-scoped for immediate availability.
        # Remove any stale global registration so Discord does not show each
        # slash command twice in the development guild.
        self.tree.clear_commands(guild=None)
        await self.tree.sync()

    async def on_ready(self) -> None:
        self._create_readiness_marker()

    async def on_disconnect(self) -> None:
        self._remove_readiness_marker()

    async def close(self) -> None:
        self._remove_readiness_marker()
        await super().close()

    @property
    def configured_cog_names(self) -> tuple[str, ...]:
        return tuple(type(cog).__name__ for cog in self._pending_cogs)

    def configure_cogs(self, cogs: Sequence[commands.Cog]) -> None:
        if self._are_cogs_installed or self._pending_cogs:
            raise RuntimeError("Discord cogs have already been configured")
        self._pending_cogs = tuple(cogs)

    def _create_readiness_marker(self) -> None:
        try:
            self._readiness_marker_path.touch(exist_ok=True)
        except OSError:
            _LOGGER.exception("could_not_create_discord_readiness_marker")

    def _remove_readiness_marker(self) -> None:
        try:
            self._readiness_marker_path.unlink(missing_ok=True)
        except OSError:
            _LOGGER.exception("could_not_remove_discord_readiness_marker")
