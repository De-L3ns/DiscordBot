from __future__ import annotations

from dataclasses import dataclass

from kletserbot.apps.wielermanager.domain.cycling_standing import CyclingStanding


@dataclass(frozen=True, slots=True)
class CyclingMovement:
    team_name: str
    old_rank: int | None
    new_rank: int | None
    points_change: int


@dataclass(frozen=True, slots=True)
class CyclingLeaderboard:
    standings: tuple[CyclingStanding, ...]

    def __post_init__(self) -> None:
        sorted_standings = tuple(sorted(self.standings, key=lambda standing: standing.rank))
        team_names = [standing.team_name for standing in sorted_standings]
        ranks = [standing.rank for standing in sorted_standings]
        if len(team_names) != len(set(team_names)):
            raise ValueError("team names must be unique")
        if len(ranks) != len(set(ranks)):
            raise ValueError("ranks must be unique")
        object.__setattr__(self, "standings", sorted_standings)

    def compare(
        self,
        previous: CyclingLeaderboard,
    ) -> tuple[CyclingMovement, ...]:
        previous_by_team = {standing.team_name: standing for standing in previous.standings}
        current_by_team = {standing.team_name: standing for standing in self.standings}
        movements: list[CyclingMovement] = []

        for current_standing in self.standings:
            previous_standing = previous_by_team.get(current_standing.team_name)
            if previous_standing is None:
                movements.append(
                    CyclingMovement(
                        team_name=current_standing.team_name,
                        old_rank=None,
                        new_rank=current_standing.rank,
                        points_change=current_standing.points,
                    )
                )
                continue
            if (
                current_standing.rank == previous_standing.rank
                and current_standing.points == previous_standing.points
            ):
                continue
            movements.append(
                CyclingMovement(
                    team_name=current_standing.team_name,
                    old_rank=previous_standing.rank,
                    new_rank=current_standing.rank,
                    points_change=(current_standing.points - previous_standing.points),
                )
            )

        for previous_standing in previous.standings:
            if previous_standing.team_name in current_by_team:
                continue
            movements.append(
                CyclingMovement(
                    team_name=previous_standing.team_name,
                    old_rank=previous_standing.rank,
                    new_rank=None,
                    points_change=-previous_standing.points,
                )
            )

        return tuple(movements)
