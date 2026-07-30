import pytest

from kletserbot.apps.general.application.reaction_roles.dto.reaction_role_request_dto import (
    ReactionRoleAction,
    ReactionRoleRequestDto,
)
from kletserbot.apps.general.application.reaction_roles.reaction_role_service import (
    ReactionRoleService,
)


def request_for_message(message_id: int) -> ReactionRoleRequestDto:
    return ReactionRoleRequestDto(
        message_id=message_id,
        guild_id=10,
        user_id=20,
        emoji_name="Game",
        action=ReactionRoleAction.ADD,
    )


def test_unrelated_reaction_returns_no_instruction() -> None:
    service = ReactionRoleService(reaction_role_message_id=100)

    assert service.determine_instruction(request_for_message(999)) is None


def test_relevant_reaction_uses_emoji_name_as_role_name() -> None:
    service = ReactionRoleService(reaction_role_message_id=100)

    result = service.determine_instruction(request_for_message(100))

    assert result is not None
    assert result.role_name == "Game"
    assert result.action is ReactionRoleAction.ADD
    assert result.guild_id == 10
    assert result.user_id == 20


def test_request_rejects_empty_emoji_name() -> None:
    with pytest.raises(ValueError, match="emoji_name"):
        ReactionRoleRequestDto(
            message_id=100,
            guild_id=10,
            user_id=20,
            emoji_name=" ",
            action=ReactionRoleAction.REMOVE,
        )
