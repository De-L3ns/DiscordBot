import asyncio
import sqlite3
from pathlib import Path

from kletserbot.apps.cardpacks.application.dto.pack_inventory_dto import (
    PackInventoryDto,
)
from kletserbot.apps.cardpacks.application.exceptions import CardpackPersistenceError


class PackInventoryPersistenceError(CardpackPersistenceError):
    """Raised when SQLite cannot complete an inventory operation."""


class SqlitePackInventoryRepository:
    def __init__(
        self,
        database_path: Path,
        *,
        busy_timeout_seconds: float = 5.0,
    ) -> None:
        if busy_timeout_seconds <= 0:
            raise ValueError("busy timeout must be positive")
        self._database_path = database_path
        self._busy_timeout_seconds = busy_timeout_seconds

    async def initialize(self) -> None:
        try:
            await asyncio.to_thread(self._initialize_synchronously)
        except (OSError, sqlite3.Error) as error:
            raise PackInventoryPersistenceError(
                "cardpack inventory could not be initialized"
            ) from error

    async def gift_packs(
        self,
        discord_user_id: int,
        set_id: str,
        amount: int,
    ) -> None:
        _validate_inventory_input(discord_user_id, set_id)
        if amount <= 0:
            raise ValueError("gift amount must be positive")
        try:
            await asyncio.to_thread(
                self._gift_packs_synchronously,
                discord_user_id,
                set_id,
                amount,
            )
        except sqlite3.Error as error:
            raise PackInventoryPersistenceError(
                "cardpack inventory could not be updated"
            ) from error

    async def consume_pack(
        self,
        discord_user_id: int,
        set_id: str,
    ) -> bool:
        _validate_inventory_input(discord_user_id, set_id)
        try:
            return await asyncio.to_thread(
                self._consume_pack_synchronously,
                discord_user_id,
                set_id,
            )
        except sqlite3.Error as error:
            raise PackInventoryPersistenceError(
                "cardpack inventory could not be updated"
            ) from error

    async def retrieve_inventory(
        self,
        discord_user_id: int,
    ) -> tuple[PackInventoryDto, ...]:
        if discord_user_id <= 0:
            raise ValueError("Discord user ID must be positive")
        try:
            return await asyncio.to_thread(
                self._retrieve_inventory_synchronously,
                discord_user_id,
            )
        except sqlite3.Error as error:
            raise PackInventoryPersistenceError(
                "cardpack inventory could not be retrieved"
            ) from error

    def _initialize_synchronously(self) -> None:
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS pack_inventory (
                    discord_user_id TEXT NOT NULL,
                    set_id TEXT NOT NULL,
                    quantity INTEGER NOT NULL CHECK (quantity >= 0),
                    PRIMARY KEY (discord_user_id, set_id)
                )
                """
            )

    def _gift_packs_synchronously(
        self,
        discord_user_id: int,
        set_id: str,
        amount: int,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO pack_inventory (discord_user_id, set_id, quantity)
                VALUES (?, ?, ?)
                ON CONFLICT (discord_user_id, set_id)
                DO UPDATE SET quantity = quantity + excluded.quantity
                """,
                (str(discord_user_id), set_id, amount),
            )

    def _consume_pack_synchronously(
        self,
        discord_user_id: int,
        set_id: str,
    ) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE pack_inventory
                SET quantity = quantity - 1
                WHERE discord_user_id = ? AND set_id = ? AND quantity > 0
                """,
                (str(discord_user_id), set_id),
            )
            return cursor.rowcount == 1

    def _retrieve_inventory_synchronously(
        self,
        discord_user_id: int,
    ) -> tuple[PackInventoryDto, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT set_id, quantity
                FROM pack_inventory
                WHERE discord_user_id = ? AND quantity > 0
                ORDER BY set_id
                """,
                (str(discord_user_id),),
            ).fetchall()
        return tuple(PackInventoryDto(set_id=str(row[0]), quantity=int(row[1])) for row in rows)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self._database_path,
            timeout=self._busy_timeout_seconds,
        )
        connection.execute(f"PRAGMA busy_timeout = {round(self._busy_timeout_seconds * 1_000)}")
        connection.execute("PRAGMA foreign_keys = ON")
        return connection


def _validate_inventory_input(discord_user_id: int, set_id: str) -> None:
    if discord_user_id <= 0:
        raise ValueError("Discord user ID must be positive")
    if not set_id:
        raise ValueError("set ID must not be empty")
