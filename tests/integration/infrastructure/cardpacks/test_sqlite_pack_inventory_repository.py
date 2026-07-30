import asyncio
from pathlib import Path

from kletserbot.application.cardpacks.dto.pack_inventory_dto import (
    PackInventoryDto,
)
from kletserbot.infrastructure.cardpacks.sqlite_pack_inventory_repository import (
    SqlitePackInventoryRepository,
)


async def test_inventory_survives_repository_recreation(tmp_path: Path) -> None:
    database_path = tmp_path / "cardpacks.sqlite3"
    first_repository = SqlitePackInventoryRepository(database_path)
    await first_repository.initialize()
    await first_repository.gift_packs(
        discord_user_id=123,
        set_id="sv3pt5",
        amount=2,
    )

    second_repository = SqlitePackInventoryRepository(database_path)
    await second_repository.initialize()

    assert await second_repository.retrieve_inventory(123) == (
        PackInventoryDto(set_id="sv3pt5", quantity=2),
    )


async def test_gifting_accumulates_and_inventory_is_sorted(tmp_path: Path) -> None:
    repository = SqlitePackInventoryRepository(tmp_path / "cardpacks.sqlite3")
    await repository.initialize()

    await repository.gift_packs(123, "sv3pt5", 2)
    await repository.gift_packs(123, "sv3pt5", 3)
    await repository.gift_packs(123, "base1", 1)

    assert await repository.retrieve_inventory(123) == (
        PackInventoryDto(set_id="base1", quantity=1),
        PackInventoryDto(set_id="sv3pt5", quantity=5),
    )


async def test_consumption_never_makes_inventory_negative(tmp_path: Path) -> None:
    repository = SqlitePackInventoryRepository(tmp_path / "cardpacks.sqlite3")
    await repository.initialize()
    await repository.gift_packs(123, "base1", 1)

    first_result = await repository.consume_pack(123, "base1")
    second_result = await repository.consume_pack(123, "base1")

    assert first_result is True
    assert second_result is False
    assert await repository.retrieve_inventory(123) == ()


async def test_concurrent_consumers_cannot_spend_the_same_pack(
    tmp_path: Path,
) -> None:
    repository = SqlitePackInventoryRepository(tmp_path / "cardpacks.sqlite3")
    await repository.initialize()
    await repository.gift_packs(123, "base1", 1)

    results = await asyncio.gather(
        repository.consume_pack(123, "base1"),
        repository.consume_pack(123, "base1"),
    )

    assert sorted(results) == [False, True]
    assert await repository.retrieve_inventory(123) == ()
