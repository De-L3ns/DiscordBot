from typing import Protocol

from kletserbot.apps.wielermanager.domain.cycling_leaderboard import CyclingLeaderboard


class CyclingLeagueGateway(Protocol):
    async def retrieve_leaderboard(self) -> CyclingLeaderboard: ...
