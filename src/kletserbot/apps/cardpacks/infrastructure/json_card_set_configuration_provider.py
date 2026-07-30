import json
import logging
import re
from collections.abc import Mapping
from pathlib import Path
from typing import cast

from kletserbot.apps.cardpacks.application.exceptions import CardpackConfigurationError
from kletserbot.apps.cardpacks.domain.pack_configuration import (
    CardFinish,
    CardKind,
    CardSetConfiguration,
    InvalidPackConfigurationError,
    PackSlotConfiguration,
    PackSlotOutcome,
)

logger = logging.getLogger(__name__)

_SET_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,49}$")
_MAX_CONFIGURED_SETS = 100
_MAX_SLOTS_PER_SET = 20
_MAX_OUTCOMES_PER_SLOT = 20
_MAX_RARITIES_PER_OUTCOME = 20
_MAX_ENERGY_CARDS_PER_SET = 20


class InvalidCardpackConfigurationFileError(CardpackConfigurationError):
    """Raised when cardpack JSON files cannot be parsed safely."""


class JsonCardSetConfigurationProvider:
    def __init__(
        self,
        set_catalog_path: Path,
        pull_rates_path: Path,
    ) -> None:
        self._set_catalog_path = set_catalog_path
        self._pull_rates_path = pull_rates_path

    def retrieve_configurations(self) -> tuple[CardSetConfiguration, ...]:
        set_catalog = _require_mapping(_read_json(self._set_catalog_path), "set catalog")
        _require_exact_keys(set_catalog, {"pokemonSets"}, "set catalog")
        configured_sets = _require_list(
            set_catalog.get("pokemonSets"),
            "pokemonSets",
            maximum_length=_MAX_CONFIGURED_SETS,
        )
        pull_rates = _require_mapping(
            _read_json(self._pull_rates_path),
            "pull-rate configuration",
        )

        configurations: list[CardSetConfiguration] = []
        seen_set_ids: set[str] = set()
        for configured_set_value in configured_sets:
            safe_set_id = "<invalid>"
            try:
                configured_set = _require_mapping(configured_set_value, "configured set")
                safe_set_id = _require_set_id(configured_set.get("id"))
                if safe_set_id in seen_set_ids:
                    raise InvalidPackConfigurationError(
                        f"duplicate configured set ID: {safe_set_id}"
                    )
                seen_set_ids.add(safe_set_id)
                pull_rate_value = pull_rates.get(safe_set_id)
                if pull_rate_value is None:
                    raise InvalidPackConfigurationError(
                        f"pull rates are missing for set {safe_set_id}"
                    )
                configurations.append(_parse_configuration(configured_set, pull_rate_value))
            except (InvalidCardpackConfigurationFileError, InvalidPackConfigurationError) as error:
                logger.warning(
                    "card_set_configuration_invalid set_id=%s reason=%s",
                    safe_set_id,
                    error,
                )
        return tuple(configurations)


def _read_json(path: Path) -> object:
    try:
        with path.open(encoding="utf-8") as configuration_file:
            return cast(object, json.load(configuration_file))
    except json.JSONDecodeError as error:
        raise InvalidCardpackConfigurationFileError(
            "cardpack configuration is not valid JSON"
        ) from error
    except OSError as error:
        raise InvalidCardpackConfigurationFileError(
            "cardpack configuration could not be read"
        ) from error


def _parse_configuration(
    configured_set: Mapping[str, object],
    pull_rate_value: object,
) -> CardSetConfiguration:
    _require_exact_keys(
        configured_set,
        {
            "id",
            "name",
            "packImageAsset",
            "energySetId",
            "energyCardIds",
        },
        "configured set",
    )
    set_id = _require_set_id(configured_set.get("id"))
    energy_set_id = _require_set_id(configured_set.get("energySetId"))
    energy_card_values = _require_list(
        configured_set.get("energyCardIds"),
        "energyCardIds",
        maximum_length=_MAX_ENERGY_CARDS_PER_SET,
    )
    energy_card_ids = tuple(_require_set_id(value) for value in energy_card_values)
    if len(set(energy_card_ids)) != len(energy_card_ids):
        raise InvalidPackConfigurationError("energyCardIds must be unique")
    name = _require_string(configured_set.get("name"), "set name", maximum_length=100)
    pack_image_asset = _require_string(
        configured_set.get("packImageAsset"),
        "pack image asset",
        maximum_length=100,
    )
    if Path(pack_image_asset).name != pack_image_asset or Path(
        pack_image_asset
    ).suffix.casefold() not in {".jpg", ".jpeg", ".png", ".webp"}:
        raise InvalidPackConfigurationError("pack image asset is not a safe image filename")
    pull_rate = _require_mapping(
        pull_rate_value,
        f"pull rates for set {set_id}",
    )
    _require_exact_keys(pull_rate, {"slots"}, f"pull rates for set {set_id}")
    slot_templates = _require_list(
        pull_rate.get("slots"),
        f"slots for set {set_id}",
        maximum_length=_MAX_SLOTS_PER_SET,
    )

    slots: list[PackSlotConfiguration] = []
    for slot_template_value in slot_templates:
        slot_template = _require_mapping(slot_template_value, "slot")
        _require_exact_keys(slot_template, {"count", "isHidden", "outcomes"}, "slot")
        count = _require_integer(
            slot_template.get("count"),
            "slot count",
            minimum=1,
            maximum=_MAX_SLOTS_PER_SET,
        )
        is_hidden = _require_boolean(slot_template.get("isHidden"), "isHidden")
        outcome_values = _require_list(
            slot_template.get("outcomes"),
            "slot outcomes",
            maximum_length=_MAX_OUTCOMES_PER_SLOT,
        )
        outcomes = tuple(_parse_outcome(value) for value in outcome_values)
        slots.extend(
            PackSlotConfiguration(outcomes=outcomes, is_hidden=is_hidden) for _ in range(count)
        )
        if len(slots) > _MAX_SLOTS_PER_SET:
            raise InvalidPackConfigurationError(
                f"set {set_id} has more than {_MAX_SLOTS_PER_SET} expanded slots"
            )

    return CardSetConfiguration(
        set_id=set_id,
        name=name,
        pack_image_asset=pack_image_asset,
        slots=tuple(slots),
        energy_set_id=energy_set_id,
        energy_card_ids=energy_card_ids,
    )


def _parse_outcome(value: object) -> PackSlotOutcome:
    outcome = _require_mapping(value, "slot outcome")
    _require_exact_keys(
        outcome,
        {
            "cardKind",
            "eligibleRarities",
            "weight",
            "finish",
            "isHit",
        },
        "slot outcome",
    )
    try:
        card_kind = CardKind(_require_string(outcome.get("cardKind"), "cardKind", 40))
    except ValueError as error:
        raise InvalidPackConfigurationError("cardKind is not supported") from error
    try:
        finish = CardFinish(_require_string(outcome.get("finish"), "finish", 40))
    except ValueError as error:
        raise InvalidPackConfigurationError("finish is not supported") from error

    rarity_values = _require_list(
        outcome.get("eligibleRarities"),
        "eligibleRarities",
        maximum_length=_MAX_RARITIES_PER_OUTCOME,
        allow_empty=True,
    )
    eligible_rarities = tuple(
        _require_string(rarity, "eligible rarity", maximum_length=60) for rarity in rarity_values
    )
    if len(set(eligible_rarities)) != len(eligible_rarities):
        raise InvalidPackConfigurationError("eligible rarities must be unique")

    return PackSlotOutcome(
        card_kind=card_kind,
        eligible_rarities=eligible_rarities,
        weight=_require_number(outcome.get("weight"), "weight"),
        finish=finish,
        is_hit=_require_boolean(outcome.get("isHit"), "isHit"),
    )


def _require_mapping(value: object, name: str) -> Mapping[str, object]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise InvalidCardpackConfigurationFileError(f"{name} must be a JSON object")
    return cast(dict[str, object], value)


def _require_list(
    value: object,
    name: str,
    *,
    maximum_length: int,
    allow_empty: bool = False,
) -> list[object]:
    if not isinstance(value, list):
        raise InvalidCardpackConfigurationFileError(f"{name} must be a JSON array")
    values = cast(list[object], value)
    if (not allow_empty and not values) or len(values) > maximum_length:
        bounds = f"between 1 and {maximum_length}"
        if allow_empty:
            bounds = f"at most {maximum_length}"
        raise InvalidCardpackConfigurationFileError(f"{name} must contain {bounds} values")
    return values


def _require_exact_keys(
    value: Mapping[str, object],
    expected_keys: set[str],
    name: str,
) -> None:
    actual_keys = set(value)
    if actual_keys != expected_keys:
        raise InvalidCardpackConfigurationFileError(
            f"{name} fields must be exactly: {', '.join(sorted(expected_keys))}"
        )


def _require_string(
    value: object,
    name: str,
    maximum_length: int,
) -> str:
    if not isinstance(value, str):
        raise InvalidCardpackConfigurationFileError(f"{name} must be a string")
    normalized_value = value.strip()
    if not normalized_value or len(normalized_value) > maximum_length:
        raise InvalidCardpackConfigurationFileError(
            f"{name} must contain between 1 and {maximum_length} characters"
        )
    return normalized_value


def _require_set_id(value: object) -> str:
    set_id = _require_string(value, "set ID", maximum_length=50)
    if _SET_ID_PATTERN.fullmatch(set_id) is None:
        raise InvalidPackConfigurationError("set ID contains unsupported characters")
    return set_id


def _require_integer(
    value: object,
    name: str,
    *,
    minimum: int,
    maximum: int,
) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise InvalidCardpackConfigurationFileError(f"{name} must be an integer")
    if not minimum <= value <= maximum:
        raise InvalidCardpackConfigurationFileError(
            f"{name} must be between {minimum} and {maximum}"
        )
    return value


def _require_number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise InvalidCardpackConfigurationFileError(f"{name} must be a number")
    return float(value)


def _require_boolean(value: object, name: str) -> bool:
    if not isinstance(value, bool):
        raise InvalidCardpackConfigurationFileError(f"{name} must be a boolean")
    return value
