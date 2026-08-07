from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dotenv import load_dotenv


class InvalidConfigurationError(ValueError):
    """Raised when runtime configuration is missing or invalid."""


_DEFAULT_CARDPACK_CONFIG_DIRECTORY = (
    Path(__file__).parents[1] / "apps" / "cardpacks" / "infrastructure" / "config"
)


@dataclass(frozen=True, slots=True)
class ApplicationSettings:
    discord_token: str
    birthday_channel_id: int
    reaction_role_message_id: int
    imgur_client_id: str
    imgur_album_key: str
    sporza_league_url: str
    is_wielermanager_polling_enabled: bool
    wielermanager_channel_id: int | None
    wielermanager_poll_interval_minutes: int
    bot_timezone: ZoneInfo
    discord_development_guild_id: int | None
    cardpack_set_catalog_path: Path
    cardpack_pull_rates_path: Path
    cardpack_data_directory: Path
    cardpack_hit_channel_id: int | None
    pokemon_tcg_api_key: str | None
    http_timeout_seconds: float
    http_max_attempts: int

    @classmethod
    def from_environment(
        cls,
        environment: Mapping[str, str] | None = None,
    ) -> ApplicationSettings:
        if environment is None:
            load_dotenv()
            environment = os.environ

        is_polling_enabled = _parse_boolean(
            environment.get("ENABLE_WIELERMANAGER_POLLING", "false"),
            "ENABLE_WIELERMANAGER_POLLING",
        )
        polling_channel_id = _parse_optional_positive_integer(
            environment.get("WIELERMANAGER_CHANNEL_ID"),
            "WIELERMANAGER_CHANNEL_ID",
        )
        if is_polling_enabled and polling_channel_id is None:
            raise InvalidConfigurationError(
                "WIELERMANAGER_CHANNEL_ID is required when polling is enabled"
            )

        sporza_league_url = _require_value(environment, "SPORZA_LEAGUE_URL")
        parsed_sporza_url = urlparse(sporza_league_url)
        if parsed_sporza_url.scheme != "https" or not parsed_sporza_url.hostname:
            raise InvalidConfigurationError("SPORZA_LEAGUE_URL must be an absolute HTTPS URL")

        timezone_name = environment.get("BOT_TIMEZONE", "Europe/Brussels")
        try:
            bot_timezone = ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError as error:
            raise InvalidConfigurationError(
                f"BOT_TIMEZONE is not a known timezone: {timezone_name}"
            ) from error

        return cls(
            discord_token=_require_value(environment, "DISCORD_TOKEN"),
            birthday_channel_id=_parse_positive_integer(
                _require_value(environment, "BIRTHDAY_CHANNEL_ID"),
                "BIRTHDAY_CHANNEL_ID",
            ),
            reaction_role_message_id=_parse_positive_integer(
                _require_value(environment, "REACTION_ROLE_MESSAGE_ID"),
                "REACTION_ROLE_MESSAGE_ID",
            ),
            imgur_client_id=_require_value(environment, "IMGUR_CLIENT_ID"),
            imgur_album_key=_require_value(environment, "IMGUR_ALBUM_KEY"),
            sporza_league_url=sporza_league_url,
            is_wielermanager_polling_enabled=is_polling_enabled,
            wielermanager_channel_id=polling_channel_id,
            wielermanager_poll_interval_minutes=_parse_bounded_integer(
                environment.get("WIELERMANAGER_POLL_INTERVAL_MINUTES", "15"),
                "WIELERMANAGER_POLL_INTERVAL_MINUTES",
                minimum=1,
                maximum=1_440,
            ),
            bot_timezone=bot_timezone,
            discord_development_guild_id=_parse_optional_positive_integer(
                environment.get("DISCORD_DEVELOPMENT_GUILD_ID"),
                "DISCORD_DEVELOPMENT_GUILD_ID",
            ),
            cardpack_set_catalog_path=_parse_optional_path(
                environment.get("CARDPACK_SET_CATALOG_PATH"),
                str(_DEFAULT_CARDPACK_CONFIG_DIRECTORY / "sets.json"),
                "CARDPACK_SET_CATALOG_PATH",
            ),
            cardpack_pull_rates_path=_parse_optional_path(
                environment.get("CARDPACK_PULL_RATES_PATH"),
                str(_DEFAULT_CARDPACK_CONFIG_DIRECTORY / "pull_rates.json"),
                "CARDPACK_PULL_RATES_PATH",
            ),
            cardpack_data_directory=_parse_optional_path(
                environment.get("CARDPACK_DATA_DIRECTORY"),
                "data/cardpacks",
                "CARDPACK_DATA_DIRECTORY",
            ),
            cardpack_hit_channel_id=_parse_optional_positive_integer(
                environment.get("CARDPACK_HIT_CHANNEL_ID"),
                "CARDPACK_HIT_CHANNEL_ID",
            ),
            pokemon_tcg_api_key=_parse_optional_secret(
                environment.get("POKEMON_TCG_API_KEY"),
                "POKEMON_TCG_API_KEY",
            ),
            http_timeout_seconds=_parse_positive_float(
                environment.get("HTTP_TIMEOUT_SECONDS", "10"),
                "HTTP_TIMEOUT_SECONDS",
            ),
            http_max_attempts=_parse_bounded_integer(
                environment.get("HTTP_MAX_ATTEMPTS", "3"),
                "HTTP_MAX_ATTEMPTS",
                minimum=1,
                maximum=5,
            ),
        )


def _require_value(environment: Mapping[str, str], name: str) -> str:
    value = environment.get(name, "").strip()
    if not value:
        raise InvalidConfigurationError(f"{name} is required")
    return value


def _parse_positive_integer(value: str, name: str) -> int:
    return _parse_bounded_integer(value, name, minimum=1)


def _parse_optional_positive_integer(value: str | None, name: str) -> int | None:
    if value is None or not value.strip():
        return None
    return _parse_positive_integer(value, name)


def _parse_bounded_integer(
    value: str,
    name: str,
    *,
    minimum: int,
    maximum: int | None = None,
) -> int:
    try:
        parsed_value = int(value)
    except ValueError as error:
        raise InvalidConfigurationError(f"{name} must be an integer") from error

    if parsed_value < minimum or (maximum is not None and parsed_value > maximum):
        bounds = f"at least {minimum}"
        if maximum is not None:
            bounds = f"between {minimum} and {maximum}"
        raise InvalidConfigurationError(f"{name} must be {bounds}")
    return parsed_value


def _parse_boolean(value: str, name: str) -> bool:
    normalized_value = value.strip().lower()
    if normalized_value == "true":
        return True
    if normalized_value == "false":
        return False
    raise InvalidConfigurationError(f"{name} must be true or false")


def _parse_positive_float(value: str, name: str) -> float:
    try:
        parsed_value = float(value)
    except ValueError as error:
        raise InvalidConfigurationError(f"{name} must be a number") from error
    if parsed_value <= 0:
        raise InvalidConfigurationError(f"{name} must be positive")
    return parsed_value


def _parse_safe_path(value: str, name: str) -> Path:
    normalized_value = value.strip()
    if not normalized_value or "\x00" in normalized_value:
        raise InvalidConfigurationError(f"{name} must be a non-empty path")
    configured_path = Path(normalized_value)
    if ".." in configured_path.parts:
        raise InvalidConfigurationError(f"{name} must not contain parent traversal")
    if configured_path.is_absolute() and configured_path == Path(configured_path.anchor):
        raise InvalidConfigurationError(f"{name} must not be a filesystem root")
    return configured_path


def _parse_optional_path(
    value: str | None,
    default_value: str,
    name: str,
) -> Path:
    selected_value = default_value if value is None or not value.strip() else value
    return _parse_safe_path(selected_value, name)


def _parse_optional_secret(value: str | None, name: str) -> str | None:
    if value is None or not value.strip():
        return None
    normalized_value = value.strip()
    if len(normalized_value) > 512:
        raise InvalidConfigurationError(f"{name} must contain at most 512 characters")
    return normalized_value
