from collections.abc import Sequence

import pytest

from kletserbot.apps.general.application.exceptions import EmptyExternalResultError
from kletserbot.apps.general.application.nostalgia.dto.nostalgia_image_dto import (
    NostalgiaImageDto,
)
from kletserbot.apps.general.application.nostalgia.nostalgia_service import NostalgiaService


class FakeImageAlbumGateway:
    def __init__(self, images: tuple[NostalgiaImageDto, ...]) -> None:
        self._images = images

    async def retrieve_images(self) -> tuple[NostalgiaImageDto, ...]:
        return self._images


def select_first(
    images: Sequence[NostalgiaImageDto],
) -> NostalgiaImageDto:
    return images[0]


@pytest.mark.asyncio
async def test_nostalgia_returns_selected_image() -> None:
    expected = NostalgiaImageDto(
        title="Eentje uit de oude doos",
        image_url="https://i.imgur.com/example.jpg",
    )
    service = NostalgiaService(FakeImageAlbumGateway((expected,)), select_first)

    assert await service.retrieve_image() == expected


@pytest.mark.asyncio
async def test_nostalgia_rejects_empty_album() -> None:
    service = NostalgiaService(FakeImageAlbumGateway(()), select_first)

    with pytest.raises(EmptyExternalResultError):
        await service.retrieve_image()


def test_nostalgia_image_requires_https_url() -> None:
    with pytest.raises(ValueError, match="image_url"):
        NostalgiaImageDto(title="Image", image_url="http://example.test/image")
