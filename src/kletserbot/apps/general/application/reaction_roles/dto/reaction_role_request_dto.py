from dataclasses import dataclass
from enum import StrEnum


class ReactionRoleAction(StrEnum):
    ADD = "add"
    REMOVE = "remove"


@dataclass(frozen=True, slots=True)
class ReactionRoleRequestDto:
    message_id: int
    guild_id: int
    user_id: int
    emoji_name: str
    action: ReactionRoleAction

    def __post_init__(self) -> None:
        if min(self.message_id, self.guild_id, self.user_id) < 1:
            raise ValueError("Discord identifiers must be positive")
        normalized_emoji_name = self.emoji_name.strip()
        if not normalized_emoji_name:
            raise ValueError("emoji_name must not be empty")
        object.__setattr__(self, "emoji_name", normalized_emoji_name)
