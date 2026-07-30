from collections.abc import Mapping, Sequence

from kletserbot.apps.cardpacks.domain.pokemon_card import (
    InvalidPokemonCardError,
    PokemonCard,
)
from kletserbot.shared.application.exceptions import InvalidExternalResponseError

_MAX_CARDS_PER_SET = 10_000
_MAX_SUBTYPES_PER_CARD = 20


def map_complete_payload(payload: object) -> tuple[PokemonCard, ...]:
    response = _require_mapping(payload, "Pokémon card response")
    raw_cards = _require_sequence(response.get("data"), "Pokémon card data")
    if not raw_cards or len(raw_cards) > _MAX_CARDS_PER_SET:
        raise InvalidExternalResponseError(
            f"Pokémon card data must contain between 1 and {_MAX_CARDS_PER_SET} cards"
        )
    return tuple(_map_card(raw_card) for raw_card in raw_cards)


def validate_page_payload(
    payload: object,
    *,
    expected_page: int,
) -> Mapping[str, object]:
    response = _require_mapping(payload, "Pokémon card response")
    raw_cards = _require_sequence(response.get("data"), "Pokémon card data")
    page = _require_integer(response.get("page"), "page", minimum=1)
    page_size = _require_integer(
        response.get("pageSize"),
        "pageSize",
        minimum=1,
        maximum=250,
    )
    count = _require_integer(response.get("count"), "count", minimum=0)
    total_count = _require_integer(
        response.get("totalCount"),
        "totalCount",
        minimum=1,
        maximum=_MAX_CARDS_PER_SET,
    )
    if page != expected_page:
        raise InvalidExternalResponseError("Pokémon card response page is inconsistent")
    if count != len(raw_cards) or count > page_size or total_count < count:
        raise InvalidExternalResponseError("Pokémon card pagination is inconsistent")
    for raw_card in raw_cards:
        _map_card(raw_card)
    return response


def _map_card(value: object) -> PokemonCard:
    raw_card = _require_mapping(value, "Pokémon card")
    raw_images = _require_mapping(raw_card.get("images"), "Pokémon card images")
    raw_subtypes_value = raw_card.get("subtypes")
    raw_subtypes = (
        ()
        if raw_subtypes_value is None
        else _require_sequence(raw_subtypes_value, "Pokémon card subtypes")
    )
    if len(raw_subtypes) > _MAX_SUBTYPES_PER_CARD:
        raise InvalidExternalResponseError(
            "Pokémon card subtypes contain an invalid number of values"
        )
    subtypes = tuple(_require_string(subtype, "Pokémon card subtype") for subtype in raw_subtypes)
    try:
        return PokemonCard(
            card_id=_require_string(raw_card.get("id"), "Pokémon card ID"),
            name=_require_string(raw_card.get("name"), "Pokémon card name"),
            number=_require_string(raw_card.get("number"), "Pokémon card number"),
            rarity=_map_optional_rarity(raw_card.get("rarity")),
            supertype=_require_string(
                raw_card.get("supertype"),
                "Pokémon card supertype",
            ),
            subtypes=subtypes,
            small_image_url=_require_string(
                raw_images.get("small"),
                "Pokémon card small image URL",
            ),
            large_image_url=_require_string(
                raw_images.get("large"),
                "Pokémon card large image URL",
            ),
        )
    except InvalidPokemonCardError as error:
        raise InvalidExternalResponseError("Pokémon card violates card invariants") from error


def _require_mapping(value: object, name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value):
        raise InvalidExternalResponseError(f"{name} must be an object")
    return value


def _require_sequence(value: object, name: str) -> Sequence[object]:
    if not isinstance(value, Sequence) or isinstance(
        value,
        (str, bytes, bytearray),
    ):
        raise InvalidExternalResponseError(f"{name} must be a list")
    return value


def _require_string(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 2_048:
        raise InvalidExternalResponseError(f"{name} must be a non-empty string")
    return value


def _map_optional_rarity(value: object) -> str:
    if value is None:
        return "Unknown"
    return _require_string(value, "Pokémon card rarity")


def _require_integer(
    value: object,
    name: str,
    *,
    minimum: int,
    maximum: int | None = None,
) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise InvalidExternalResponseError(f"{name} must be an integer")
    if value < minimum or (maximum is not None and value > maximum):
        raise InvalidExternalResponseError(f"{name} is outside supported bounds")
    return value
