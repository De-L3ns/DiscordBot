from collections.abc import Mapping

import pytest

from kletserbot.application.exceptions import (
    ExternalServiceUnavailableError,
    InvalidExternalResponseError,
)
from kletserbot.infrastructure.sporza.indexed_payload_decoder import (
    IndexedPayloadDecoder,
)
from kletserbot.infrastructure.sporza.sporza_cycling_client import (
    SporzaCyclingClient,
)


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


class InvalidJsonResponse(FakeResponse):
    async def json(self) -> object:
        raise ValueError("invalid JSON")


class FakeSession:
    def __init__(
        self,
        responses: list[FakeResponse] | None = None,
        error: Exception | None = None,
    ) -> None:
        self._responses = responses or []
        self._error = error
        self.calls = 0

    def get(
        self,
        url: str,
        *,
        timeout: object,
        headers: Mapping[str, str] | None = None,
    ) -> FakeResponse:
        del url, timeout, headers
        self.calls += 1
        if self._error is not None:
            raise self._error
        return self._responses.pop(0)


@pytest.mark.asyncio
async def test_client_maps_legacy_payload() -> None:
    session = FakeSession(
        [FakeResponse({"teams": [{"rank": 1, "name": "Fast Team", "points": 100}]})]
    )
    client = SporzaCyclingClient(
        session,  # type: ignore[arg-type]
        "https://example.test/sporza",
        IndexedPayloadDecoder(),
        max_attempts=1,
    )

    result = await client.retrieve_leaderboard()

    assert result.standings[0].team_name == "Fast Team"


@pytest.mark.asyncio
async def test_client_retries_timeout_and_raises_stable_error() -> None:
    session = FakeSession(error=TimeoutError())
    client = SporzaCyclingClient(
        session,  # type: ignore[arg-type]
        "https://example.test/sporza",
        IndexedPayloadDecoder(),
        max_attempts=2,
        retry_delay_seconds=0,
    )

    with pytest.raises(ExternalServiceUnavailableError):
        await client.retrieve_leaderboard()

    assert session.calls == 2


@pytest.mark.asyncio
async def test_client_rejects_malformed_payload() -> None:
    session = FakeSession([FakeResponse({"teams": [{"rank": "bad"}]})])
    client = SporzaCyclingClient(
        session,  # type: ignore[arg-type]
        "https://example.test/sporza",
        IndexedPayloadDecoder(),
        max_attempts=1,
    )

    with pytest.raises(InvalidExternalResponseError):
        await client.retrieve_leaderboard()


@pytest.mark.asyncio
async def test_client_translates_invalid_json() -> None:
    session = FakeSession([InvalidJsonResponse(None)])
    client = SporzaCyclingClient(
        session,  # type: ignore[arg-type]
        "https://example.test/sporza",
        IndexedPayloadDecoder(),
        max_attempts=1,
    )

    with pytest.raises(InvalidExternalResponseError):
        await client.retrieve_leaderboard()
