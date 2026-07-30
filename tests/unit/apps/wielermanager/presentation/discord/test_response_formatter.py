from datetime import UTC, datetime

from kletserbot.apps.wielermanager.application.dto.cycling_leaderboard_dto import (
    CyclingLeaderboardDto,
)
from kletserbot.apps.wielermanager.application.dto.cycling_movement_dto import (
    CyclingMovementDto,
)
from kletserbot.apps.wielermanager.application.dto.cycling_standing_dto import (
    CyclingStandingDto,
)
from kletserbot.apps.wielermanager.presentation.discord.response_formatter import (
    format_cycling_leaderboard,
)


def test_leaderboard_is_formatted_as_discord_code_block() -> None:
    leaderboard = CyclingLeaderboardDto(
        standings=(CyclingStandingDto(rank=1, team_name="Fast Team", points=110),),
        movements=(),
        retrieved_at_utc=datetime(2026, 7, 23, 12, tzinfo=UTC),
    )

    result = format_cycling_leaderboard(leaderboard)

    assert result.startswith("```")
    assert "# | Team" in result
    assert "1 | Fast Team" in result
    assert "Last update: 23-07-26 - 12:00:00 UTC" in result
    assert result.endswith("```")


def test_leaderboard_movements_are_rendered_outside_table() -> None:
    leaderboard = CyclingLeaderboardDto(
        standings=(CyclingStandingDto(rank=1, team_name="Fast Team", points=110),),
        movements=(
            CyclingMovementDto(
                team_name="Fast Team",
                old_rank=2,
                new_rank=1,
                points_change=10,
            ),
        ),
        retrieved_at_utc=datetime(2026, 7, 23, 12, tzinfo=UTC),
    )

    result = format_cycling_leaderboard(leaderboard)

    assert "🚴 Fast Team kreeg 10 punten bij en stijgt naar plaats 1" in result
