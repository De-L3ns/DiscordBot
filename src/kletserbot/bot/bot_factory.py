import random
from collections.abc import Sequence
from datetime import UTC, datetime

import aiohttp
from discord.ext import commands

from kletserbot.apps.cardpacks.application.cardpack_service import CardpackService
from kletserbot.apps.cardpacks.domain.pack_generator import PackGenerator
from kletserbot.apps.cardpacks.infrastructure.cached_pokemon_card_catalog import (
    CachedPokemonCardCatalog,
)
from kletserbot.apps.cardpacks.infrastructure.json_card_set_configuration_provider import (
    JsonCardSetConfigurationProvider,
)
from kletserbot.apps.cardpacks.infrastructure.json_pokemon_card_cache import (
    JsonPokemonCardCache,
)
from kletserbot.apps.cardpacks.infrastructure.pokemon_tcg_client import (
    PokemonTcgClient,
)
from kletserbot.apps.cardpacks.infrastructure.sqlite_pack_inventory_repository import (
    SqlitePackInventoryRepository,
)
from kletserbot.apps.cardpacks.presentation.discord.cardpacks_cog import CardpacksCog
from kletserbot.apps.general.application.birthdays.birthday_service import BirthdayService
from kletserbot.apps.general.application.nostalgia.nostalgia_service import NostalgiaService
from kletserbot.apps.general.application.quotes.quote_service import QuoteService
from kletserbot.apps.general.application.reaction_roles.reaction_role_service import (
    ReactionRoleService,
)
from kletserbot.apps.general.infrastructure.imgur.imgur_album_client import ImgurAlbumClient
from kletserbot.apps.general.infrastructure.static_content.static_birthday_provider import (
    StaticBirthdayProvider,
)
from kletserbot.apps.general.infrastructure.static_content.static_quote_provider import (
    StaticQuoteProvider,
)
from kletserbot.apps.general.presentation.discord.birthdays_cog import BirthdayCog
from kletserbot.apps.general.presentation.discord.general_cog import GeneralCog
from kletserbot.apps.general.presentation.discord.reaction_roles_cog import ReactionRolesCog
from kletserbot.apps.wielermanager.application.wielermanager_service import (
    WielermanagerService,
)
from kletserbot.apps.wielermanager.infrastructure.sporza.indexed_payload_decoder import (
    IndexedPayloadDecoder,
)
from kletserbot.apps.wielermanager.infrastructure.sporza.sporza_cycling_client import (
    SporzaCyclingClient,
)
from kletserbot.apps.wielermanager.presentation.discord.wielermanager_cog import (
    WielermanagerCog,
)
from kletserbot.bot.application_settings import (
    ApplicationSettings,
)
from kletserbot.bot.discord_bot import KletserBot


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
    pokemon_tcg_client = PokemonTcgClient(
        http_session=http_session,
        api_key=settings.pokemon_tcg_api_key,
        timeout_seconds=settings.http_timeout_seconds,
        max_attempts=settings.http_max_attempts,
    )
    pokemon_card_cache = JsonPokemonCardCache(settings.cardpack_data_directory / "cache")
    pokemon_card_catalog = CachedPokemonCardCatalog(
        pokemon_tcg_client,
        pokemon_card_cache,
    )
    cardpack_service = CardpackService(
        configuration_provider=JsonCardSetConfigurationProvider(
            settings.cardpack_set_catalog_path,
            settings.cardpack_pull_rates_path,
        ),
        card_catalog=pokemon_card_catalog,
        inventory_repository=SqlitePackInventoryRepository(
            settings.cardpack_data_directory / "inventory.sqlite3"
        ),
        pack_generator=PackGenerator(),
        random_value=random.random,
        select_card=_select_random,
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
        CardpacksCog(cardpack_service),
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
