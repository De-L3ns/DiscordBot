import asyncio
import logging

import aiohttp

from kletserbot.bot_factory import create_bot
from kletserbot.infrastructure.configuration.application_settings import (
    ApplicationSettings,
)


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format=("%(asctime)s %(levelname)s %(name)s operation=%(message)s"),
    )
    settings = ApplicationSettings.from_environment()
    async with aiohttp.ClientSession() as http_session:
        bot = create_bot(settings, http_session)
        async with bot:
            await bot.start(settings.discord_token)


if __name__ == "__main__":
    asyncio.run(main())
