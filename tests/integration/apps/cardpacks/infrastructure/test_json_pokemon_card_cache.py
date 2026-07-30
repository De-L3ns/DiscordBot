import json
from pathlib import Path

import pytest

from kletserbot.apps.cardpacks.infrastructure.json_pokemon_card_cache import (
    InvalidPokemonCardCacheError,
    JsonPokemonCardCache,
    PokemonCardCacheUnavailableError,
)


def card_payload(card_id: str) -> dict[str, object]:
    return {
        "id": card_id,
        "name": f"Card {card_id}",
        "number": card_id.rsplit("-", maxsplit=1)[-1],
        "rarity": "Common",
        "supertype": "Pokémon",
        "subtypes": ["Basic"],
        "images": {
            "small": f"https://images.example.test/{card_id}.png",
            "large": f"https://images.example.test/{card_id}_large.png",
        },
        "artist": "Full payload survives",
    }


def page_payload(
    cards: list[dict[str, object]],
    *,
    page: int,
    total_count: int,
) -> dict[str, object]:
    return {
        "data": cards,
        "page": page,
        "pageSize": 1,
        "count": len(cards),
        "totalCount": total_count,
    }


async def test_cache_preserves_complete_payload_and_maps_cards(
    tmp_path: Path,
) -> None:
    cache = JsonPokemonCardCache(tmp_path)
    payload = page_payload([card_payload("sv3pt5-1")], page=1, total_count=1)

    await cache.store_complete_payload("sv3pt5", payload)
    cards = await cache.retrieve_cards("sv3pt5")

    stored_payload = json.loads((tmp_path / "sv3pt5.json").read_text(encoding="utf-8"))
    assert stored_payload["data"][0]["artist"] == "Full payload survives"
    assert cards[0].card_id == "sv3pt5-1"
    assert cards[0].small_image_url.endswith("sv3pt5-1.png")


async def test_invalid_payload_does_not_replace_valid_cache(tmp_path: Path) -> None:
    cache = JsonPokemonCardCache(tmp_path)
    valid_payload = page_payload(
        [card_payload("sv3pt5-1")],
        page=1,
        total_count=1,
    )
    await cache.store_complete_payload("sv3pt5", valid_payload)

    with pytest.raises(InvalidPokemonCardCacheError):
        await cache.store_complete_payload("sv3pt5", {"data": [{"id": 123}]})

    assert (await cache.retrieve_cards("sv3pt5"))[0].card_id == "sv3pt5-1"


async def test_missing_cache_has_stable_unavailable_error(tmp_path: Path) -> None:
    cache = JsonPokemonCardCache(tmp_path)

    with pytest.raises(
        PokemonCardCacheUnavailableError,
        match="cached cards are unavailable",
    ):
        await cache.retrieve_cards("base1")


async def test_cache_rejects_unsafe_set_id(tmp_path: Path) -> None:
    cache = JsonPokemonCardCache(tmp_path)

    with pytest.raises(ValueError, match="set ID contains unsupported characters"):
        await cache.retrieve_cards("../inventory")


async def test_missing_optional_rarity_is_mapped_outside_configured_pools(
    tmp_path: Path,
) -> None:
    cache = JsonPokemonCardCache(tmp_path)
    energy_without_rarity = card_payload("sve-9")
    energy_without_rarity.pop("rarity")
    energy_without_rarity["name"] = "Basic Grass Energy"
    energy_without_rarity["supertype"] = "Energy"
    payload = page_payload(
        [energy_without_rarity],
        page=1,
        total_count=1,
    )

    await cache.store_complete_payload("sve", payload)
    cached_card = (await cache.retrieve_cards("sve"))[0]

    assert cached_card.rarity == "Unknown"
    assert cached_card.is_basic_energy is True


async def test_missing_legacy_subtypes_maps_to_empty_tuple(tmp_path: Path) -> None:
    cache = JsonPokemonCardCache(tmp_path)
    legacy_trainer = card_payload("base1-91")
    legacy_trainer.pop("subtypes")
    legacy_trainer["name"] = "Bill"
    legacy_trainer["supertype"] = "Trainer"
    payload = page_payload([legacy_trainer], page=1, total_count=1)

    await cache.store_complete_payload("base1", payload)
    cached_card = (await cache.retrieve_cards("base1"))[0]

    assert cached_card.subtypes == ()
    assert cached_card.rarity == "Common"
