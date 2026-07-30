from collections.abc import Mapping

import pytest

from kletserbot.apps.general.infrastructure.imgur.imgur_album_client import ImgurAlbumClient
from kletserbot.shared.application.exceptions import (
    ExternalServiceUnavailableError,
    InvalidExternalResponseError,
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
    def __init__(self, response: FakeResponse) -> None:
        self._response = response
        self.headers: Mapping[str, str] | None = None

    def get(
        self,
        url: str,
        *,
        timeout: object,
        headers: Mapping[str, str] | None = None,
    ) -> FakeResponse:
        del url, timeout
        self.headers = headers
        return self._response


@pytest.mark.asyncio
async def test_client_maps_valid_images() -> None:
    session = FakeSession(FakeResponse({"data": [{"link": "https://i.imgur.com/photo.jpg"}]}))
    client = ImgurAlbumClient(
        session,  # type: ignore[arg-type]
        client_id="client-id",
        album_key="album",
        max_attempts=1,
    )

    images = await client.retrieve_images()

    assert images[0].image_url == "https://i.imgur.com/photo.jpg"
    assert session.headers == {"Authorization": "Client-ID client-id"}


@pytest.mark.asyncio
async def test_client_translates_server_failure() -> None:
    session = FakeSession(FakeResponse({}, status=503))
    client = ImgurAlbumClient(
        session,  # type: ignore[arg-type]
        client_id="client-id",
        album_key="album",
        max_attempts=1,
    )

    with pytest.raises(ExternalServiceUnavailableError):
        await client.retrieve_images()


@pytest.mark.asyncio
async def test_client_rejects_invalid_payload() -> None:
    session = FakeSession(FakeResponse({"data": "not-a-list"}))
    client = ImgurAlbumClient(
        session,  # type: ignore[arg-type]
        client_id="client-id",
        album_key="album",
        max_attempts=1,
    )

    with pytest.raises(InvalidExternalResponseError):
        await client.retrieve_images()


@pytest.mark.asyncio
async def test_client_translates_invalid_json() -> None:
    session = FakeSession(InvalidJsonResponse(None))
    client = ImgurAlbumClient(
        session,  # type: ignore[arg-type]
        client_id="client-id",
        album_key="album",
        max_attempts=1,
    )

    with pytest.raises(InvalidExternalResponseError):
        await client.retrieve_images()
