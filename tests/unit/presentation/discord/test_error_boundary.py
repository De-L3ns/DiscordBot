import pytest

from kletserbot.presentation.discord.general_cog import GeneralCog


class FailingQuoteService:
    def retrieve_quote(self) -> None:
        raise RuntimeError("unexpected internal detail")


class UnusedNostalgiaService:
    pass


class FakeResponse:
    def __init__(self) -> None:
        self.content: str | None = None
        self.ephemeral = False

    async def send_message(
        self,
        content: str,
        *,
        ephemeral: bool = False,
    ) -> None:
        self.content = content
        self.ephemeral = ephemeral


class FakeInteraction:
    def __init__(self) -> None:
        self.response = FakeResponse()


@pytest.mark.asyncio
async def test_unexpected_command_error_returns_safe_response() -> None:
    cog = GeneralCog(
        FailingQuoteService(),  # type: ignore[arg-type]
        UnusedNostalgiaService(),  # type: ignore[arg-type]
    )
    interaction = FakeInteraction()

    await cog.citaat.callback(cog, interaction)  # type: ignore[arg-type]

    assert interaction.response.ephemeral is True
    assert interaction.response.content == "Er ging onverwacht iets mis."
    assert "internal detail" not in interaction.response.content
