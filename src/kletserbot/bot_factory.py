import random
from collections.abc import Sequence
from datetime import UTC, datetime

import aiohttp
from discord.ext import commands

from kletserbot.application.birthdays.birthday_service import BirthdayService
from kletserbot.application.nostalgia.nostalgia_service import NostalgiaService
from kletserbot.application.quotes.quote_service import QuoteService
from kletserbot.application.reaction_roles.reaction_role_service import (
    ReactionRoleService,
)
from kletserbot.application.wielermanager.wielermanager_service import (
    WielermanagerService,
)
from kletserbot.infrastructure.configuration.application_settings import (
    ApplicationSettings,
)
from kletserbot.infrastructure.imgur.imgur_album_client import ImgurAlbumClient
from kletserbot.infrastructure.sporza.indexed_payload_decoder import (
    IndexedPayloadDecoder,
)
from kletserbot.infrastructure.sporza.sporza_cycling_client import (
    SporzaCyclingClient,
)
from kletserbot.infrastructure.static_content.static_birthday_provider import (
    StaticBirthdayProvider,
)
from kletserbot.infrastructure.static_content.static_quote_provider import (
    StaticQuoteProvider,
)
from kletserbot.presentation.discord.birthdays_cog import BirthdayCog
from kletserbot.presentation.discord.bot import KletserBot
from kletserbot.presentation.discord.general_cog import GeneralCog
from kletserbot.presentation.discord.reaction_roles_cog import ReactionRolesCog
from kletserbot.presentation.discord.wielermanager_cog import (
    WielermanagerCog,
)


def create_bot(
    settings: ApplicationSettings,
    http_session: aiohttp.ClientSession,
) -> KletserBot:
    imgur_album_client = ImgurAlbumClient(
        http_session=http_session,
        client_id=settings.imgur_client_id,
        album_key=settings.imgur_album_key,
        timeout_seconds=settings.http_timeout_seconds,
        max_attempts=settings.http_max_attempts,
    )
    sporza_cycling_client = SporzaCyclingClient(
        http_session=http_session,
        league_url=settings.sporza_league_url,
        payload_decoder=IndexedPayloadDecoder(),
        timeout_seconds=settings.http_timeout_seconds,
        max_attempts=settings.http_max_attempts,
    )

    birthday_service = BirthdayService(
        StaticBirthdayProvider(),
        _select_random,
    )
    quote_service = QuoteService(StaticQuoteProvider(), _select_random)
    nostalgia_service = NostalgiaService(
        imgur_album_client,
        _select_random,
    )
    reaction_role_service = ReactionRoleService(settings.reaction_role_message_id)
    wielermanager_service = WielermanagerService(
        sporza_cycling_client,
        _utc_now,
    )

    bot = KletserBot(
        cogs=(),
        development_guild_id=settings.discord_development_guild_id,
    )
    cogs: tuple[commands.Cog, ...] = (
        BirthdayCog(
            bot=bot,
            birthday_service=birthday_service,
            birthday_channel_id=settings.birthday_channel_id,
            timezone=settings.bot_timezone,
        ),
        GeneralCog(
            quote_service=quote_service,
            nostalgia_service=nostalgia_service,
        ),
        ReactionRolesCog(
            bot=bot,
            reaction_role_service=reaction_role_service,
        ),
        WielermanagerCog(
            bot=bot,
            wielermanager_service=wielermanager_service,
            is_polling_enabled=(settings.is_wielermanager_polling_enabled),
            polling_channel_id=settings.wielermanager_channel_id,
            polling_interval_minutes=(settings.wielermanager_poll_interval_minutes),
        ),
    )
    bot.configure_cogs(cogs)
    return bot


def _select_random[SelectionValue](
    values: Sequence[SelectionValue],
) -> SelectionValue:
    return random.choice(values)


def _utc_now() -> datetime:
    return datetime.now(UTC)
