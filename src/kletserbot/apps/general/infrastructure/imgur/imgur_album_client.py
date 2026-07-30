import asyncio
from collections.abc import Mapping, Sequence

import aiohttp

from kletserbot.apps.general.application.nostalgia.dto.nostalgia_image_dto import (
    NostalgiaImageDto,
)
from kletserbot.shared.application.exceptions import (
    ExternalServiceUnavailableError,
    InvalidExternalResponseError,
)


class ImgurAlbumClient:
    _API_ROOT = "https://api.imgur.com/3"

    def __init__(
        self,
        http_session: aiohttp.ClientSession,
        client_id: str,
        album_key: str,
        *,
        timeout_seconds: float = 10,
        max_attempts: int = 3,
        retry_delay_seconds: float = 0.25,
    ) -> None:
        self._http_session = http_session
        self._client_id = client_id
        self._album_key = album_key
        self._timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        self._max_attempts = max_attempts
        self._retry_delay_seconds = retry_delay_seconds

    async def retrieve_images(self) -> tuple[NostalgiaImageDto, ...]:
        payload = await self._retrieve_payload()
        if not isinstance(payload, Mapping):
            raise InvalidExternalResponseError("Imgur response must be an object")
        raw_images = payload.get("data")
        if not isinstance(raw_images, Sequence) or isinstance(
            raw_images,
            (str, bytes, bytearray),
        ):
            raise InvalidExternalResponseError("Imgur response data must be a list")

        images: list[NostalgiaImageDto] = []
        for raw_image in raw_images:
            if not isinstance(raw_image, Mapping):
                raise InvalidExternalResponseError("Imgur image entry must be an object")
            image_url = raw_image.get("link")
            if not isinstance(image_url, str):
                raise InvalidExternalResponseError("Imgur image entry is missing its link")
            try:
                images.append(
                    NostalgiaImageDto(
                        title="Eentje uit de oude doos",
                        image_url=image_url,
                    )
                )
            except ValueError as error:
                raise InvalidExternalResponseError("Imgur returned an invalid image URL") from error
        return tuple(images)

    async def _retrieve_payload(self) -> object:
        image_url = f"{self._API_ROOT}/album/{self._album_key}/images"
        headers = {"Authorization": f"Client-ID {self._client_id}"}
        for attempt in range(1, self._max_attempts + 1):
            try:
                async with self._http_session.get(
                    image_url,
                    headers=headers,
                    timeout=self._timeout,
                ) as response:
                    if response.status == 200:
                        try:
                            return await response.json()
                        except ValueError as error:
                            raise InvalidExternalResponseError(
                                "Imgur returned invalid JSON"
                            ) from error
                    if response.status != 429 and response.status < 500:
                        raise InvalidExternalResponseError(f"Imgur returned HTTP {response.status}")
            except (TimeoutError, aiohttp.ClientError) as error:
                if attempt == self._max_attempts:
                    raise ExternalServiceUnavailableError("Imgur is unavailable") from error

            if attempt < self._max_attempts:
                await asyncio.sleep(self._retry_delay_seconds * attempt)

        raise ExternalServiceUnavailableError("Imgur is unavailable")
