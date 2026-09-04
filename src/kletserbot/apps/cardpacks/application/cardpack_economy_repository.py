from datetime import date, datetime
from typing import Protocol

from kletserbot.apps.cardpacks.application.dto.cardshop_dto import PointMutationResultDto


class CardpackEconomyRepository(Protocol):
    async def initialize(self) -> None: ...

    async def retrieve_point_balance(self, discord_user_id: int) -> int: ...

    async def claim_daily_points(
        self,
        discord_user_id: int,
        claim_date: date,
        points: int,
        created_at_utc: datetime,
    ) -> PointMutationResultDto: ...

    async def grant_points(
        self,
        discord_user_id: int,
        actor_discord_user_id: int,
        points: int,
        created_at_utc: datetime,
    ) -> int: ...

    async def purchase_packs(
        self,
        discord_user_id: int,
        set_id: str,
        quantity: int,
        total_price: int,
        created_at_utc: datetime,
    ) -> int | None: ...
