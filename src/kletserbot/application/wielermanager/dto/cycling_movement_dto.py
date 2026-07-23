from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CyclingMovementDto:
    team_name: str
    old_rank: int | None
    new_rank: int | None
    points_change: int
