from dataclasses import dataclass

from kletserbot.application.reaction_roles.dto.reaction_role_request_dto import (
    ReactionRoleAction,
)


@dataclass(frozen=True, slots=True)
class ReactionRoleInstructionDto:
    guild_id: int
    user_id: int
    role_name: str
    action: ReactionRoleAction
