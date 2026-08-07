import asyncio
import sqlite3
from pathlib import Path

from kletserbot.apps.cardpacks.application.dto.collection_card_dto import (
    CollectionCardDto,
)
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

    async def consume_pack_and_store_cards(
        self,
        discord_user_id: int,
        set_id: str,
        cards: tuple[CollectionCardDto, ...],
    ) -> bool:
        _validate_inventory_input(discord_user_id, set_id)
        try:
            return await asyncio.to_thread(
                self._consume_pack_and_store_cards_synchronously,
                discord_user_id,
                set_id,
                cards,
            )
        except sqlite3.Error as error:
            raise PackInventoryPersistenceError(
                "cardpack collection could not be updated"
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

    async def retrieve_collection(
        self,
        discord_user_id: int,
    ) -> tuple[CollectionCardDto, ...]:
        if discord_user_id <= 0:
            raise ValueError("Discord user ID must be positive")
        try:
            return await asyncio.to_thread(
                self._retrieve_collection_synchronously,
                discord_user_id,
            )
        except sqlite3.Error as error:
            raise PackInventoryPersistenceError(
                "cardpack collection could not be retrieved"
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
            self._initialize_collection_table(connection)

    @staticmethod
    def _initialize_collection_table(connection: sqlite3.Connection) -> None:
        columns = connection.execute("PRAGMA table_info(card_collection)").fetchall()
        if columns and any(str(column[1]) == "finish" for column in columns):
            connection.execute(
                """
                CREATE TABLE card_collection_new (
                    discord_user_id TEXT NOT NULL, set_id TEXT NOT NULL,
                    set_name TEXT NOT NULL, card_id TEXT NOT NULL, name TEXT NOT NULL,
                    number TEXT NOT NULL, rarity TEXT NOT NULL, thumbnail_url TEXT NOT NULL,
                    image_url TEXT NOT NULL, quantity INTEGER NOT NULL CHECK (quantity > 0),
                    PRIMARY KEY (discord_user_id, set_id, card_id)
                )
                """
            )
            connection.execute(
                """
                INSERT INTO card_collection_new
                SELECT discord_user_id, set_id, MAX(set_name), card_id, MAX(name),
                       MAX(number), MAX(rarity), MAX(thumbnail_url), MAX(image_url),
                       SUM(quantity)
                FROM card_collection
                GROUP BY discord_user_id, set_id, card_id
                """
            )
            connection.execute("DROP TABLE card_collection")
            connection.execute("ALTER TABLE card_collection_new RENAME TO card_collection")
            return
        if columns and not any(str(column[1]) == "quantity" for column in columns):
            connection.execute(
                "ALTER TABLE card_collection ADD COLUMN quantity INTEGER NOT NULL DEFAULT 1"
            )
            return
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS card_collection (
                discord_user_id TEXT NOT NULL, set_id TEXT NOT NULL,
                set_name TEXT NOT NULL, card_id TEXT NOT NULL, name TEXT NOT NULL,
                number TEXT NOT NULL, rarity TEXT NOT NULL, thumbnail_url TEXT NOT NULL,
                image_url TEXT NOT NULL, quantity INTEGER NOT NULL CHECK (quantity > 0),
                PRIMARY KEY (discord_user_id, set_id, card_id)
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

    def _consume_pack_and_store_cards_synchronously(
        self,
        discord_user_id: int,
        set_id: str,
        cards: tuple[CollectionCardDto, ...],
    ) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE pack_inventory SET quantity = quantity - 1
                WHERE discord_user_id = ? AND set_id = ? AND quantity > 0
                """,
                (str(discord_user_id), set_id),
            )
            if cursor.rowcount != 1:
                return False
            for card in cards:
                connection.execute(
                    """
                    INSERT INTO card_collection (
                        discord_user_id, set_id, set_name, card_id, name, number,
                        rarity, thumbnail_url, image_url, quantity
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                    ON CONFLICT (discord_user_id, set_id, card_id)
                    DO UPDATE SET quantity = quantity + 1
                    """,
                    (
                        str(discord_user_id), card.set_id, card.set_name,
                        card.card_id, card.name, card.number, card.rarity,
                        card.thumbnail_url, card.image_url,
                    ),
                )
            return True

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

    def _retrieve_collection_synchronously(
        self,
        discord_user_id: int,
    ) -> tuple[CollectionCardDto, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT set_id, set_name, card_id, name, number, rarity,
                       thumbnail_url, image_url, quantity
                FROM card_collection
                WHERE discord_user_id = ?
                ORDER BY set_id, CAST(number AS INTEGER), number, card_id
                """,
                (str(discord_user_id),),
            ).fetchall()
        return tuple(
            CollectionCardDto(
                set_id=str(row[0]), set_name=str(row[1]), card_id=str(row[2]),
                name=str(row[3]), number=str(row[4]), rarity=str(row[5]),
                thumbnail_url=str(row[6]), image_url=str(row[7]), quantity=int(row[8]),
            )
            for row in rows
        )

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
