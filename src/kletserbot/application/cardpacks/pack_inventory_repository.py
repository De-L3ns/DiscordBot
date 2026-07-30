from typing import Protocol

from kletserbot.application.cardpacks.dto.pack_inventory_dto import (
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

    async def retrieve_inventory(
        self,
        discord_user_id: int,
    ) -> tuple[PackInventoryDto, ...]: ...
