from pathlib import Path

import pytest

from kletserbot.bot.discord_bot import KletserBot


@pytest.mark.asyncio
async def test_ready_state_creates_and_disconnect_removes_marker(tmp_path: Path) -> None:
    readiness_marker_path = tmp_path / "kletserbot-ready"
    bot = KletserBot(
        cogs=(),
        development_guild_id=None,
        readiness_marker_path=readiness_marker_path,
    )

    await bot.on_ready()

    assert readiness_marker_path.is_file()

    await bot.on_disconnect()

    assert not readiness_marker_path.exists()


def test_constructor_removes_a_stale_readiness_marker(tmp_path: Path) -> None:
    readiness_marker_path = tmp_path / "kletserbot-ready"
    readiness_marker_path.touch()

    KletserBot(
        cogs=(),
        development_guild_id=None,
        readiness_marker_path=readiness_marker_path,
    )

    assert not readiness_marker_path.exists()
