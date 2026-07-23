import pytest

from kletserbot.domain.cycling.cycling_leaderboard import CyclingLeaderboard
from kletserbot.domain.cycling.cycling_standing import CyclingStanding


def leaderboard(*standings: CyclingStanding) -> CyclingLeaderboard:
    return CyclingLeaderboard(standings)


def test_compare_reports_points_and_rank_changes() -> None:
    previous = leaderboard(
        CyclingStanding(rank=2, team_name="Fast Team", points=100),
        CyclingStanding(rank=1, team_name="Other Team", points=105),
    )
    current = leaderboard(
        CyclingStanding(rank=1, team_name="Fast Team", points=110),
        CyclingStanding(rank=2, team_name="Other Team", points=105),
    )

    movements = current.compare(previous)

    fast_team = next(movement for movement in movements if movement.team_name == "Fast Team")
    assert fast_team.points_change == 10
    assert fast_team.old_rank == 2
    assert fast_team.new_rank == 1


def test_compare_reports_new_and_missing_teams() -> None:
    previous = leaderboard(CyclingStanding(rank=1, team_name="Old Team", points=100))
    current = leaderboard(CyclingStanding(rank=1, team_name="New Team", points=50))

    movements = current.compare(previous)

    assert {(item.team_name, item.old_rank, item.new_rank) for item in movements} == {
        ("New Team", None, 1),
        ("Old Team", 1, None),
    }


def test_standings_are_sorted_by_rank() -> None:
    result = leaderboard(
        CyclingStanding(rank=2, team_name="Second", points=10),
        CyclingStanding(rank=1, team_name="First", points=20),
    )

    assert tuple(item.team_name for item in result.standings) == (
        "First",
        "Second",
    )


@pytest.mark.parametrize(
    "standing_values",
    [
        {"rank": 0, "team_name": "Team", "points": 1},
        {"rank": 1, "team_name": " ", "points": 1},
        {"rank": 1, "team_name": "Team", "points": -1},
    ],
)
def test_invalid_standing_is_rejected(
    standing_values: dict[str, int | str],
) -> None:
    with pytest.raises(ValueError):
        CyclingStanding(**standing_values)  # type: ignore[arg-type]
