from kletserbot.apps.cardpacks.application.cardshop_message_repository import (
    CardshopMessageRepository,
)


class CardshopMessageService:
    def __init__(self, repository: CardshopMessageRepository) -> None:
        self._repository = repository

    async def initialize(self) -> None:
        await self._repository.initialize()

    async def retrieve_message_id(self, channel_id: int) -> int | None:
        return await self._repository.retrieve_message_id(channel_id)

    async def store_message_id(self, channel_id: int, message_id: int) -> None:
        await self._repository.store_message_id(channel_id, message_id)
