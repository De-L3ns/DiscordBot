from zoneinfo import ZoneInfo

import pytest

from kletserbot.bot.application_settings import (
    ApplicationSettings,
    InvalidConfigurationError,
)


@pytest.fixture
def valid_environment() -> dict[str, str]:
    return {
        "DISCORD_TOKEN": "test-discord-token",
        "BIRTHDAY_CHANNEL_ID": "100",
        "REACTION_ROLE_MESSAGE_ID": "200",
        "IMGUR_CLIENT_ID": "test-imgur-client",
        "IMGUR_ALBUM_KEY": "test-album",
        "SPORZA_LEAGUE_URL": "https://example.test/sporza",
    }


def test_settings_load_required_values(valid_environment: dict[str, str]) -> None:
    settings = ApplicationSettings.from_environment(valid_environment)

    assert settings.discord_token == "test-discord-token"
    assert settings.birthday_channel_id == 100
    assert settings.reaction_role_message_id == 200
    assert settings.imgur_client_id == "test-imgur-client"
    assert settings.imgur_album_key == "test-album"
    assert settings.sporza_league_url == "https://example.test/sporza"


def test_polling_is_disabled_by_default(valid_environment: dict[str, str]) -> None:
    settings = ApplicationSettings.from_environment(valid_environment)

    assert settings.is_wielermanager_polling_enabled is False
    assert settings.wielermanager_channel_id is None
    assert settings.wielermanager_poll_interval_minutes == 15


def test_polling_channel_is_required_when_polling_is_enabled(
    valid_environment: dict[str, str],
) -> None:
    valid_environment["ENABLE_WIELERMANAGER_POLLING"] = "true"

    with pytest.raises(
        InvalidConfigurationError,
        match="WIELERMANAGER_CHANNEL_ID",
    ):
        ApplicationSettings.from_environment(valid_environment)


def test_default_timezone_is_europe_brussels(
    valid_environment: dict[str, str],
) -> None:
    settings = ApplicationSettings.from_environment(valid_environment)

    assert settings.bot_timezone == ZoneInfo("Europe/Brussels")


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("BIRTHDAY_CHANNEL_ID", "0"),
        ("BIRTHDAY_CHANNEL_ID", "not-an-integer"),
        ("REACTION_ROLE_MESSAGE_ID", "-1"),
    ],
)
def test_discord_identifiers_must_be_positive_integers(
    valid_environment: dict[str, str],
    name: str,
    value: str,
) -> None:
    valid_environment[name] = value

    with pytest.raises(InvalidConfigurationError, match=name):
        ApplicationSettings.from_environment(valid_environment)


def test_sporza_url_must_use_https(valid_environment: dict[str, str]) -> None:
    valid_environment["SPORZA_LEAGUE_URL"] = "http://example.test/sporza"

    with pytest.raises(InvalidConfigurationError, match="SPORZA_LEAGUE_URL"):
        ApplicationSettings.from_environment(valid_environment)


def test_invalid_boolean_is_rejected(valid_environment: dict[str, str]) -> None:
    valid_environment["ENABLE_WIELERMANAGER_POLLING"] = "sometimes"

    with pytest.raises(
        InvalidConfigurationError,
        match="ENABLE_WIELERMANAGER_POLLING",
    ):
        ApplicationSettings.from_environment(valid_environment)


def test_poll_interval_is_bounded(valid_environment: dict[str, str]) -> None:
    valid_environment["WIELERMANAGER_POLL_INTERVAL_MINUTES"] = "0"

    with pytest.raises(
        InvalidConfigurationError,
        match="WIELERMANAGER_POLL_INTERVAL_MINUTES",
    ):
        ApplicationSettings.from_environment(valid_environment)


def test_http_resilience_has_bounded_defaults(
    valid_environment: dict[str, str],
) -> None:
    settings = ApplicationSettings.from_environment(valid_environment)

    assert settings.http_timeout_seconds == 10.0
    assert settings.http_max_attempts == 3


def test_http_timeout_must_be_positive(
    valid_environment: dict[str, str],
) -> None:
    valid_environment["HTTP_TIMEOUT_SECONDS"] = "0"

    with pytest.raises(InvalidConfigurationError, match="HTTP_TIMEOUT_SECONDS"):
        ApplicationSettings.from_environment(valid_environment)


def test_cardpack_settings_have_safe_packaged_defaults(
    valid_environment: dict[str, str],
) -> None:
    settings = ApplicationSettings.from_environment(valid_environment)

    assert settings.cardpack_set_catalog_path.name == "sets.json"
    assert settings.cardpack_set_catalog_path.is_file()
    assert settings.cardpack_pull_rates_path.name == "pull_rates.json"
    assert settings.cardpack_pull_rates_path.is_file()
    assert settings.cardpack_data_directory.parts[-2:] == ("data", "cardpacks")
    assert settings.pokemon_tcg_api_key is None


def test_optional_pokemon_api_key_and_data_path_are_loaded(
    valid_environment: dict[str, str],
) -> None:
    valid_environment["POKEMON_TCG_API_KEY"] = " secret-key "
    valid_environment["CARDPACK_DATA_DIRECTORY"] = "/app/data/cardpacks"

    settings = ApplicationSettings.from_environment(valid_environment)

    assert settings.pokemon_tcg_api_key == "secret-key"
    assert str(settings.cardpack_data_directory) == "/app/data/cardpacks"


def test_cardpack_data_path_rejects_parent_traversal(
    valid_environment: dict[str, str],
) -> None:
    valid_environment["CARDPACK_DATA_DIRECTORY"] = "../outside"

    with pytest.raises(
        InvalidConfigurationError,
        match="CARDPACK_DATA_DIRECTORY",
    ):
        ApplicationSettings.from_environment(valid_environment)


def test_blank_optional_cardpack_path_overrides_use_defaults(
    valid_environment: dict[str, str],
) -> None:
    valid_environment["CARDPACK_SET_CATALOG_PATH"] = ""
    valid_environment["CARDPACK_PULL_RATES_PATH"] = ""

    settings = ApplicationSettings.from_environment(valid_environment)

    assert settings.cardpack_set_catalog_path.name == "sets.json"
    assert settings.cardpack_pull_rates_path.name == "pull_rates.json"
