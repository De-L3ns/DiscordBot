from typing import Protocol

from kletserbot.apps.general.application.nostalgia.dto.nostalgia_image_dto import (
    NostalgiaImageDto,
)


class ImageAlbumGateway(Protocol):
    async def retrieve_images(self) -> tuple[NostalgiaImageDto, ...]: ...
