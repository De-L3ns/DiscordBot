from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CyclingStandingDto:
    rank: int
    team_name: str
    points: int
