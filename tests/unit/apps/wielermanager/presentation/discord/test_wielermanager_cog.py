import pytest

from kletserbot.apps.wielermanager.presentation.discord.wielermanager_cog import (
    WielermanagerCog,
)


class FakeWielermanagerService:
    async def poll_for_movements(self) -> None:
        return None


class FakeBot:
    pass


@pytest.mark.asyncio
async def test_polling_loop_is_not_started_when_disabled() -> None:
    cog = WielermanagerCog(
        bot=FakeBot(),  # type: ignore[arg-type]
        wielermanager_service=FakeWielermanagerService(),  # type: ignore[arg-type]
        is_polling_enabled=False,
        polling_channel_id=None,
        polling_interval_minutes=15,
    )

    await cog.cog_load()

    assert cog.polling_loop.is_running() is False
