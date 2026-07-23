from collections.abc import Callable, Sequence

from kletserbot.application.exceptions import EmptyExternalResultError
from kletserbot.application.nostalgia.dto.nostalgia_image_dto import (
    NostalgiaImageDto,
)
from kletserbot.application.nostalgia.image_album_gateway import (
    ImageAlbumGateway,
)

ImageSelector = Callable[
    [Sequence[NostalgiaImageDto]],
    NostalgiaImageDto,
]


class NostalgiaService:
    def __init__(
        self,
        image_album_gateway: ImageAlbumGateway,
        image_selector: ImageSelector,
    ) -> None:
        self._image_album_gateway = image_album_gateway
        self._image_selector = image_selector

    async def retrieve_image(self) -> NostalgiaImageDto:
        images = await self._image_album_gateway.retrieve_images()
        if not images:
            raise EmptyExternalResultError("The nostalgia album is empty")
        return self._image_selector(images)
