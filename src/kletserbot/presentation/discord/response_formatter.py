from kletserbot.application.wielermanager.dto.cycling_leaderboard_dto import (
    CyclingLeaderboardDto,
)
from kletserbot.application.wielermanager.dto.cycling_movement_dto import (
    CyclingMovementDto,
)

_COLUMN_WIDTHS = (1, 20, 6)


def format_cycling_leaderboard(
    leaderboard: CyclingLeaderboardDto,
) -> str:
    lines = [
        "```",
        _format_row("#", "Team", "Points"),
        "-" * (sum(_COLUMN_WIDTHS) + 6),
    ]
    lines.extend(
        _format_row(
            str(standing.rank),
            standing.team_name[: _COLUMN_WIDTHS[1]],
            str(standing.points),
        )
        for standing in leaderboard.standings
    )
    lines.append(f"Last update: {leaderboard.retrieved_at_utc.strftime('%d-%m-%y - %H:%M:%S')} UTC")
    lines.append("```")

    if leaderboard.movements:
        lines.extend(_format_movement(item) for item in leaderboard.movements)
    return "\n".join(lines)


def _format_row(rank: str, team_name: str, points: str) -> str:
    return (
        f"{rank:<{_COLUMN_WIDTHS[0]}} | "
        f"{team_name:<{_COLUMN_WIDTHS[1]}} | "
        f"{points:<{_COLUMN_WIDTHS[2]}}"
    )


def _format_movement(movement: CyclingMovementDto) -> str:
    if movement.old_rank is None:
        return f"🚴 {movement.team_name} komt binnen op plaats {movement.new_rank}"
    if movement.new_rank is None:
        return f"🚴 {movement.team_name} staat niet langer in het klassement"

    if movement.points_change > 0:
        points_text = f"kreeg {movement.points_change} punten bij"
    elif movement.points_change < 0:
        points_text = f"verloor {abs(movement.points_change)} punten"
    else:
        points_text = "behield hetzelfde puntenaantal"

    if movement.new_rank < movement.old_rank:
        rank_text = f"en stijgt naar plaats {movement.new_rank}"
    elif movement.new_rank > movement.old_rank:
        rank_text = f"en zakt naar plaats {movement.new_rank}"
    else:
        rank_text = "en blijft op dezelfde plaats"
    return f"🚴 {movement.team_name} {points_text} {rank_text}"
