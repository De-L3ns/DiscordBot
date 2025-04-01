from dataclasses import dataclass

@dataclass
class PlayerInfo:
    def __init__(self, rank: str, team: str, points: str):
        self.rank = rank
        self.team = team
        self.points = points

    def toString(self) -> str:
        return f"{self.team} | {self.points}"