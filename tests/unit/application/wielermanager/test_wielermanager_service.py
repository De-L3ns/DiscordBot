from datetime import UTC, datetime

import pytest

from kletserbot.application.wielermanager.wielermanager_service import (
    WielermanagerService,
)
from kletserbot.domain.cycling.cycling_leaderboard import CyclingLeaderboard
from kletserbot.domain.cycling.cycling_standing import CyclingStanding


class FakeCyclingLeagueGateway:
    def __init__(self, *leaderboards: CyclingLeaderboard) -> None:
        self._leaderboards = iter(leaderboards)

    async def retrieve_leaderboard(self) -> CyclingLeaderboard:
        return next(self._leaderboards)


def fixed_utc_clock() -> datetime:
    return datetime(2026, 7, 23, 12, tzinfo=UTC)


def leaderboard(rank: int, points: int) -> CyclingLeaderboard:
    return CyclingLeaderboard((CyclingStanding(rank=rank, team_name="Fast Team", points=points),))


@pytest.mark.asyncio
async def test_first_poll_sets_baseline_without_notification() -> None:
    service = WielermanagerService(
        FakeCyclingLeagueGateway(leaderboard(1, 100)),
        fixed_utc_clock,
    )

    assert await service.poll_for_movements() is None


@pytest.mark.asyncio
async def test_later_poll_returns_movements() -> None:
    service = WielermanagerService(
        FakeCyclingLeagueGateway(
            leaderboard(2, 100),
            leaderboard(1, 110),
        ),
        fixed_utc_clock,
    )
    await service.poll_for_movements()

    result = await service.poll_for_movements()

    assert result is not None
    assert result.movements[0].points_change == 10
    assert result.movements[0].new_rank == 1
    assert result.retrieved_at_utc == fixed_utc_clock()


@pytest.mark.asyncio
async def test_no_change_returns_no_notification() -> None:
    same_table = leaderboard(1, 100)
    service = WielermanagerService(
        FakeCyclingLeagueGateway(same_table, same_table),
        fixed_utc_clock,
    )
    await service.poll_for_movements()

    assert await service.poll_for_movements() is None


@pytest.mark.asyncio
async def test_on_demand_retrieval_returns_standings() -> None:
    service = WielermanagerService(
        FakeCyclingLeagueGateway(leaderboard(1, 100)),
        fixed_utc_clock,
    )

    result = await service.retrieve_leaderboard()

    assert result.standings[0].team_name == "Fast Team"
    assert result.movements == ()
