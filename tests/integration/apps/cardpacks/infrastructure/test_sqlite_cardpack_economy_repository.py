import asyncio
import sqlite3
from datetime import UTC, date, datetime
from pathlib import Path

from kletserbot.apps.cardpacks.infrastructure.sqlite_cardpack_economy_repository import (
    SqliteCardpackEconomyRepository,
)
from kletserbot.apps.cardpacks.infrastructure.sqlite_pack_inventory_repository import (
    SqlitePackInventoryRepository,
)


def timestamp() -> datetime:
    return datetime(2026, 9, 4, 12, 0, tzinfo=UTC)


async def create_repository(database_path: Path) -> SqliteCardpackEconomyRepository:
    await SqlitePackInventoryRepository(database_path).initialize()
    repository = SqliteCardpackEconomyRepository(database_path)
    await repository.initialize()
    return repository


async def test_daily_claim_persists_once_per_date_and_records_ledger(tmp_path: Path) -> None:
    repository = await create_repository(tmp_path / "cardpacks.sqlite3")

    first_claim = await repository.claim_daily_points(123, date(2026, 9, 4), 1_000, timestamp())
    duplicate_claim = await repository.claim_daily_points(
        123,
        date(2026, 9, 4),
        1_000,
        timestamp(),
    )
    next_day_claim = await repository.claim_daily_points(
        123,
        date(2026, 9, 5),
        1_000,
        timestamp(),
    )

    assert first_claim.was_applied is True
    assert first_claim.point_balance == 1_000
    assert duplicate_claim.was_applied is False
    assert duplicate_claim.point_balance == 1_000
    assert next_day_claim.was_applied is True
    assert next_day_claim.point_balance == 2_000

    with sqlite3.connect(tmp_path / "cardpacks.sqlite3") as connection:
        ledger_rows = connection.execute(
            "SELECT transaction_kind, points_delta FROM point_transactions ORDER BY transaction_id"
        ).fetchall()
    assert ledger_rows == [("daily_claim", 1_000), ("daily_claim", 1_000)]


async def test_concurrent_daily_claims_award_points_only_once(tmp_path: Path) -> None:
    repository = await create_repository(tmp_path / "cardpacks.sqlite3")

    outcomes = await asyncio.gather(
        repository.claim_daily_points(123, date(2026, 9, 4), 1_000, timestamp()),
        repository.claim_daily_points(123, date(2026, 9, 4), 1_000, timestamp()),
    )

    assert sorted(outcome.was_applied for outcome in outcomes) == [False, True]
    assert await repository.retrieve_point_balance(123) == 1_000


async def test_purchase_debits_points_adds_inventory_and_records_ledger(tmp_path: Path) -> None:
    database_path = tmp_path / "cardpacks.sqlite3"
    repository = await create_repository(database_path)
    await repository.grant_points(123, 999, 1_000, timestamp())

    balance = await repository.purchase_packs(123, "base1", 1, 600, timestamp())

    assert balance == 400
    with sqlite3.connect(database_path) as connection:
        inventory_row = connection.execute(
            "SELECT quantity FROM pack_inventory WHERE discord_user_id = ? AND set_id = ?",
            ("123", "base1"),
        ).fetchone()
        purchase_row = connection.execute(
            """
            SELECT transaction_kind, points_delta, set_id, pack_quantity
            FROM point_transactions ORDER BY transaction_id DESC LIMIT 1
            """
        ).fetchone()
    assert inventory_row == (1,)
    assert purchase_row == ("pack_purchase", -600, "base1", 1)


async def test_concurrent_purchases_cannot_overspend_or_partially_add_inventory(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "cardpacks.sqlite3"
    repository = await create_repository(database_path)
    await repository.grant_points(123, 999, 600, timestamp())

    outcomes = await asyncio.gather(
        repository.purchase_packs(123, "base1", 1, 600, timestamp()),
        repository.purchase_packs(123, "base1", 1, 600, timestamp()),
    )

    assert sorted(outcome is None for outcome in outcomes) == [False, True]
    assert await repository.retrieve_point_balance(123) == 0
    with sqlite3.connect(database_path) as connection:
        inventory_row = connection.execute(
            "SELECT quantity FROM pack_inventory WHERE discord_user_id = ? AND set_id = ?",
            ("123", "base1"),
        ).fetchone()
    assert inventory_row == (1,)


async def test_economy_initialization_preserves_existing_inventory_and_collection_rows(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "cardpacks.sqlite3"
    inventory_repository = SqlitePackInventoryRepository(database_path)
    await inventory_repository.initialize()
    await inventory_repository.gift_packs(123, "base1", 3)
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO card_collection (
                discord_user_id, set_id, set_name, card_id, name, number, rarity,
                thumbnail_url, image_url, quantity
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "123",
                "base1",
                "Base Set",
                "base1-4",
                "Charizard",
                "4",
                "Rare Holo",
                "https://example.test/small.png",
                "https://example.test/large.png",
                2,
            ),
        )
        inventory_before = connection.execute("SELECT * FROM pack_inventory").fetchall()
        collection_before = connection.execute("SELECT * FROM card_collection").fetchall()

    await SqliteCardpackEconomyRepository(database_path).initialize()

    with sqlite3.connect(database_path) as connection:
        inventory_after = connection.execute("SELECT * FROM pack_inventory").fetchall()
        collection_after = connection.execute("SELECT * FROM card_collection").fetchall()
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
    assert inventory_after == inventory_before
    assert collection_after == collection_before
    assert {"point_accounts", "point_transactions"}.issubset(tables)
