from kletserbot.apps.general.application.reaction_roles.dto.reaction_role_instruction_dto import (
    ReactionRoleInstructionDto,
)
from kletserbot.apps.general.application.reaction_roles.dto.reaction_role_request_dto import (
    ReactionRoleRequestDto,
)


class ReactionRoleService:
    def __init__(self, reaction_role_message_id: int) -> None:
        if reaction_role_message_id < 1:
            raise ValueError("reaction_role_message_id must be positive")
        self._reaction_role_message_id = reaction_role_message_id

    def determine_instruction(
        self,
        request: ReactionRoleRequestDto,
    ) -> ReactionRoleInstructionDto | None:
        if request.message_id != self._reaction_role_message_id:
            return None
        return ReactionRoleInstructionDto(
            guild_id=request.guild_id,
            user_id=request.user_id,
            role_name=request.emoji_name,
            action=request.action,
        )
