from zoneinfo import ZoneInfo

from kletserbot.apps.general.presentation.discord.birthdays_cog import BirthdayCog


class FakeBirthdayService:
    def find_announcements(self, current_date: object) -> tuple[object, ...]:
        del current_date
        return ()


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
