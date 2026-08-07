from typing import Protocol

from kletserbot.apps.cardpacks.application.dto.collection_card_dto import (
    CollectionCardDto,
)
from kletserbot.apps.cardpacks.application.dto.pack_inventory_dto import (
    PackInventoryDto,
)


class PackInventoryRepository(Protocol):
    async def initialize(self) -> None: ...

    async def gift_packs(
        self,
        discord_user_id: int,
        set_id: str,
        amount: int,
    ) -> None: ...

    async def consume_pack(
        self,
        discord_user_id: int,
        set_id: str,
    ) -> bool: ...

    async def consume_pack_and_store_cards(
        self,
        discord_user_id: int,
        set_id: str,
        cards: tuple[CollectionCardDto, ...],
    ) -> bool: ...

    async def retrieve_inventory(
        self,
        discord_user_id: int,
    ) -> tuple[PackInventoryDto, ...]: ...

    async def retrieve_collection(
        self,
        discord_user_id: int,
    ) -> tuple[CollectionCardDto, ...]: ...
