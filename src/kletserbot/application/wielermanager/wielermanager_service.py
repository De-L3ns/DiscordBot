from collections.abc import Callable
from datetime import datetime

from kletserbot.application.wielermanager.cycling_league_gateway import (
    CyclingLeagueGateway,
)
from kletserbot.application.wielermanager.dto.cycling_leaderboard_dto import (
    CyclingLeaderboardDto,
)
from kletserbot.application.wielermanager.dto.cycling_movement_dto import (
    CyclingMovementDto,
)
from kletserbot.application.wielermanager.dto.cycling_standing_dto import (
    CyclingStandingDto,
)
from kletserbot.domain.cycling.cycling_leaderboard import (
    CyclingLeaderboard,
    CyclingMovement,
)

UtcClock = Callable[[], datetime]


class WielermanagerService:
    def __init__(
        self,
        cycling_league_gateway: CyclingLeagueGateway,
        utc_clock: UtcClock,
    ) -> None:
        self._cycling_league_gateway = cycling_league_gateway
        self._utc_clock = utc_clock
        self._previous_leaderboard: CyclingLeaderboard | None = None

    async def retrieve_leaderboard(self) -> CyclingLeaderboardDto:
        leaderboard = await self._cycling_league_gateway.retrieve_leaderboard()
        self._previous_leaderboard = leaderboard
        return self._to_dto(leaderboard, ())

    async def poll_for_movements(self) -> CyclingLeaderboardDto | None:
        leaderboard = await self._cycling_league_gateway.retrieve_leaderboard()
        previous_leaderboard = self._previous_leaderboard
        self._previous_leaderboard = leaderboard
        if previous_leaderboard is None:
            return None

        movements = leaderboard.compare(previous_leaderboard)
        if not movements:
            return None
        return self._to_dto(leaderboard, movements)

    def _to_dto(
        self,
        leaderboard: CyclingLeaderboard,
        movements: tuple[CyclingMovement, ...],
    ) -> CyclingLeaderboardDto:
        return CyclingLeaderboardDto(
            standings=tuple(
                CyclingStandingDto(
                    rank=standing.rank,
                    team_name=standing.team_name,
                    points=standing.points,
                )
                for standing in leaderboard.standings
            ),
            movements=tuple(
                CyclingMovementDto(
                    team_name=movement.team_name,
                    old_rank=movement.old_rank,
                    new_rank=movement.new_rank,
                    points_change=movement.points_change,
                )
                for movement in movements
            ),
            retrieved_at_utc=self._utc_clock(),
        )
