from typing import cast

import aiohttp

from kletserbot.bot.application_settings import (
    ApplicationSettings,
)
from kletserbot.bot.bot_factory import create_bot


def settings() -> ApplicationSettings:
    return ApplicationSettings.from_environment(
        {
            "BOT_MODE": "production",
            "DISCORD_TOKEN": "test-token",
            "BIRTHDAY_CHANNEL_ID": "100",
            "REACTION_ROLE_MESSAGE_ID": "200",
            "IMGUR_CLIENT_ID": "test-client",
            "IMGUR_ALBUM_KEY": "test-album",
            "SPORZA_LEAGUE_URL": "https://example.test/sporza",
        }
    )


def test_create_bot_composes_all_retained_features() -> None:
    http_session = cast(aiohttp.ClientSession, object())

    bot = create_bot(settings(), http_session)

    assert set(bot.configured_cog_names) == {
        "BirthdayCog",
        "CardpacksCog",
        "GeneralCog",
        "ReactionRolesCog",
        "WielermanagerCog",
    }


def test_create_bot_has_no_commands_before_discord_setup() -> None:
    http_session = cast(aiohttp.ClientSession, object())

    bot = create_bot(settings(), http_session)

    assert bot.all_commands == {}
