from typing import Protocol

from kletserbot.domain.cycling.cycling_leaderboard import CyclingLeaderboard


class CyclingLeagueGateway(Protocol):
    async def retrieve_leaderboard(self) -> CyclingLeaderboard: ...
