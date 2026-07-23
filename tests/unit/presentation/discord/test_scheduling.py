from zoneinfo import ZoneInfo

import pytest

from kletserbot.presentation.discord.birthdays_cog import BirthdayCog
from kletserbot.presentation.discord.wielermanager_cog import (
    WielermanagerCog,
)


class FakeBirthdayService:
    def find_announcements(self, current_date: object) -> tuple[object, ...]:
        del current_date
        return ()


class FakeWielermanagerService:
    async def poll_for_movements(self) -> None:
        return None


class FakeBot:
    pass


def test_birthday_schedule_uses_configured_timezone() -> None:
    cog = BirthdayCog(
        bot=FakeBot(),  # type: ignore[arg-type]
        birthday_service=FakeBirthdayService(),  # type: ignore[arg-type]
        birthday_channel_id=100,
        timezone=ZoneInfo("Europe/Brussels"),
    )

    scheduled_time = cog.birthday_loop.time[0]

    assert scheduled_time.hour == 12
    assert scheduled_time.tzinfo == ZoneInfo("Europe/Brussels")


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
