from kletserbot.presentation.discord.bot import KletserBot
from kletserbot.presentation.discord.cardpacks_cog import CardpacksCog
from kletserbot.presentation.discord.general_cog import GeneralCog
from kletserbot.presentation.discord.wielermanager_cog import (
    WielermanagerCog,
)


def test_only_retained_slash_commands_are_declared() -> None:
    command_names = {
        command.name
        for cog_type in (CardpacksCog, GeneralCog, WielermanagerCog)
        for command in cog_type.__cog_app_commands__
    }

    assert command_names == {
        "citaat",
        "giftpack",
        "nostalgie",
        "pack",
        "wielermanager",
    }


def test_bot_has_no_default_help_or_message_content_intent() -> None:
    bot = KletserBot(cogs=(), development_guild_id=None)

    assert bot.help_command is None
    assert bot.intents.message_content is False
