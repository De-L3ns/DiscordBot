from collections.abc import Mapping

import aiohttp
import pytest

from kletserbot.application.exceptions import (
    ExternalServiceUnavailableError,
    InvalidExternalResponseError,
)
from kletserbot.infrastructure.cardpacks.pokemon_tcg_client import (
    PokemonTcgClient,
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


class FakeResponse:
    def __init__(self, payload: object, status: int = 200) -> None:
        self._payload = payload
        self.status = status

    async def __aenter__(self) -> "FakeResponse":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def json(self) -> object:
        return self._payload


class FakeSession:
    def __init__(
        self,
        responses: list[FakeResponse] | None = None,
        error: Exception | None = None,
    ) -> None:
        self._responses = responses or []
        self._error = error
        self.calls: list[tuple[str, Mapping[str, str], Mapping[str, object]]] = []

    def get(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        params: Mapping[str, object],
        timeout: object,
    ) -> FakeResponse:
        del timeout
        self.calls.append((url, headers, params))
        if self._error is not None:
            raise self._error
        return self._responses.pop(0)


async def test_client_retrieves_and_combines_every_page() -> None:
    session = FakeSession(
        [
            FakeResponse(page_payload([card_payload("sv3pt5-1")], page=1, total_count=2)),
            FakeResponse(page_payload([card_payload("sv3pt5-2")], page=2, total_count=2)),
        ]
    )
    client = PokemonTcgClient(
        session,  # type: ignore[arg-type]
        api_key="secret-key",
        max_attempts=1,
        page_size=1,
    )

    complete_payload = await client.retrieve_complete_set_payload("sv3pt5")

    assert [card["id"] for card in complete_payload["data"]] == [
        "sv3pt5-1",
        "sv3pt5-2",
    ]
    assert complete_payload["count"] == 2
    assert complete_payload["totalCount"] == 2
    assert len(session.calls) == 2
    assert session.calls[0][0] == "https://api.pokemontcg.io/v2/cards"
    assert session.calls[0][1] == {"X-Api-Key": "secret-key"}
    assert session.calls[0][2] == {
        "q": "set.id:sv3pt5",
        "page": 1,
        "pageSize": 1,
    }


async def test_client_omits_api_key_header_when_not_configured() -> None:
    session = FakeSession(
        [FakeResponse(page_payload([card_payload("base1-1")], page=1, total_count=1))]
    )
    client = PokemonTcgClient(
        session,  # type: ignore[arg-type]
        api_key=None,
        max_attempts=1,
    )

    await client.retrieve_complete_set_payload("base1")

    assert session.calls[0][1] == {}


async def test_client_retries_timeout_and_raises_stable_error() -> None:
    session = FakeSession(error=TimeoutError())
    client = PokemonTcgClient(
        session,  # type: ignore[arg-type]
        api_key=None,
        max_attempts=2,
        retry_delay_seconds=0,
    )

    with pytest.raises(
        ExternalServiceUnavailableError,
        match="Pokémon TCG API is unavailable",
    ):
        await client.retrieve_complete_set_payload("base1")

    assert len(session.calls) == 2


async def test_client_rejects_malformed_card_payload() -> None:
    invalid_card = card_payload("base1-1")
    invalid_card["images"] = {"small": "not-https"}
    session = FakeSession([FakeResponse(page_payload([invalid_card], page=1, total_count=1))])
    client = PokemonTcgClient(
        session,  # type: ignore[arg-type]
        api_key=None,
        max_attempts=1,
    )

    with pytest.raises(InvalidExternalResponseError):
        await client.retrieve_complete_set_payload("base1")


async def test_client_translates_connection_errors() -> None:
    session = FakeSession(error=aiohttp.ClientConnectionError())
    client = PokemonTcgClient(
        session,  # type: ignore[arg-type]
        api_key=None,
        max_attempts=1,
    )

    with pytest.raises(ExternalServiceUnavailableError):
        await client.retrieve_complete_set_payload("base1")
