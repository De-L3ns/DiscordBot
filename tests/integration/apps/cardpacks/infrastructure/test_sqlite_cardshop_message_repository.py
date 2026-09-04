from pathlib import Path

from kletserbot.apps.cardpacks.infrastructure.sqlite_cardshop_message_repository import (
    SqliteCardshopMessageRepository,
)


async def test_cardshop_message_id_survives_repository_recreation(tmp_path: Path) -> None:
    database_path = tmp_path / "cardpacks.sqlite3"
    first_repository = SqliteCardshopMessageRepository(database_path)
    await first_repository.initialize()
    await first_repository.store_message_id(100, 200)

    second_repository = SqliteCardshopMessageRepository(database_path)
    await second_repository.initialize()

    assert await second_repository.retrieve_message_id(100) == 200


async def test_storing_replacement_message_id_overwrites_only_that_channel(tmp_path: Path) -> None:
    repository = SqliteCardshopMessageRepository(tmp_path / "cardpacks.sqlite3")
    await repository.initialize()
    await repository.store_message_id(100, 200)
    await repository.store_message_id(100, 300)
    await repository.store_message_id(101, 400)

    assert await repository.retrieve_message_id(100) == 300
    assert await repository.retrieve_message_id(101) == 400
