from dataclasses import dataclass
from datetime import datetime

from kletserbot.application.wielermanager.dto.cycling_movement_dto import (
    CyclingMovementDto,
)
from kletserbot.application.wielermanager.dto.cycling_standing_dto import (
    CyclingStandingDto,
)


@dataclass(frozen=True, slots=True)
class CyclingLeaderboardDto:
    standings: tuple[CyclingStandingDto, ...]
    movements: tuple[CyclingMovementDto, ...]
    retrieved_at_utc: datetime
