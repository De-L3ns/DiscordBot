import logging

import discord
from discord.ext import commands

from kletserbot.apps.general.application.reaction_roles.dto.reaction_role_request_dto import (
    ReactionRoleAction,
    ReactionRoleRequestDto,
)
from kletserbot.apps.general.application.reaction_roles.reaction_role_service import (
    ReactionRoleService,
)

logger = logging.getLogger(__name__)


class ReactionRolesCog(commands.Cog):
    def __init__(
        self,
        bot: commands.Bot,
        reaction_role_service: ReactionRoleService,
    ) -> None:
        self._bot = bot
        self._reaction_role_service = reaction_role_service

    @commands.Cog.listener()
    async def on_raw_reaction_add(
        self,
        payload: discord.RawReactionActionEvent,
    ) -> None:
        await self._apply_reaction(payload, ReactionRoleAction.ADD)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(
        self,
        payload: discord.RawReactionActionEvent,
    ) -> None:
        await self._apply_reaction(payload, ReactionRoleAction.REMOVE)

    async def _apply_reaction(
        self,
        payload: discord.RawReactionActionEvent,
        action: ReactionRoleAction,
    ) -> None:
        if payload.guild_id is None or payload.emoji.name is None:
            return
        try:
            request = ReactionRoleRequestDto(
                message_id=payload.message_id,
                guild_id=payload.guild_id,
                user_id=payload.user_id,
                emoji_name=payload.emoji.name,
                action=action,
            )
        except ValueError:
            logger.warning("invalid_reaction_role_event")
            return

        instruction = self._reaction_role_service.determine_instruction(request)
        if instruction is None:
            return

        guild = self._bot.get_guild(instruction.guild_id)
        if guild is None:
            logger.warning(
                "reaction_role_guild_unavailable",
                extra={"guild_id": instruction.guild_id},
            )
            return
        role = discord.utils.get(guild.roles, name=instruction.role_name)
        if role is None:
            logger.warning(
                "reaction_role_role_unavailable",
                extra={"guild_id": guild.id},
            )
            return

        member = payload.member or guild.get_member(instruction.user_id)
        if member is None:
            try:
                member = await guild.fetch_member(instruction.user_id)
            except discord.DiscordException:
                logger.exception(
                    "reaction_role_member_unavailable",
                    extra={"guild_id": guild.id},
                )
                return

        try:
            if instruction.action is ReactionRoleAction.ADD:
                await member.add_roles(role, reason="Reaction role added")
            else:
                await member.remove_roles(role, reason="Reaction role removed")
        except discord.DiscordException:
            logger.exception(
                "reaction_role_update_failed",
                extra={"guild_id": guild.id},
            )
