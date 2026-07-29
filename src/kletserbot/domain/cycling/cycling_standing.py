from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CyclingStanding:
    rank: int
    team_name: str
    points: int

    def __post_init__(self) -> None:
        normalized_team_name = self.team_name.strip()
        if self.rank < 1:
            raise ValueError("rank must be positive")
        if not normalized_team_name:
            raise ValueError("team_name must not be empty")
        if self.points < 0:
            raise ValueError("points must not be negative")
        object.__setattr__(self, "team_name", normalized_team_name)
