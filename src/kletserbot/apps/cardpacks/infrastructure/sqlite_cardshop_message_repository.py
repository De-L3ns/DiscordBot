import asyncio
import sqlite3
from pathlib import Path

from kletserbot.apps.cardpacks.application.cardshop_message_repository import (
    CardshopMessageRepository,
)
from kletserbot.apps.cardpacks.application.exceptions import CardpackPersistenceError


class CardshopMessagePersistenceError(CardpackPersistenceError):
    """Raised when SQLite cannot complete cardshop message registry work."""


class SqliteCardshopMessageRepository(CardshopMessageRepository):
    def __init__(self, database_path: Path, *, busy_timeout_seconds: float = 5.0) -> None:
        if busy_timeout_seconds <= 0:
            raise ValueError("busy timeout must be positive")
        self._database_path = database_path
        self._busy_timeout_seconds = busy_timeout_seconds

    async def initialize(self) -> None:
        try:
            await asyncio.to_thread(self._initialize_synchronously)
        except (OSError, sqlite3.Error) as error:
            raise CardshopMessagePersistenceError(
                "cardshop message registry could not be initialized"
            ) from error

    async def retrieve_message_id(self, channel_id: int) -> int | None:
        _validate_snowflake(channel_id, "channel ID")
        try:
            return await asyncio.to_thread(self._retrieve_message_id_synchronously, channel_id)
        except sqlite3.Error as error:
            raise CardshopMessagePersistenceError(
                "cardshop message registry could not be read"
            ) from error

    async def store_message_id(self, channel_id: int, message_id: int) -> None:
        _validate_snowflake(channel_id, "channel ID")
        _validate_snowflake(message_id, "message ID")
        try:
            await asyncio.to_thread(
                self._store_message_id_synchronously,
                channel_id,
                message_id,
            )
        except sqlite3.Error as error:
            raise CardshopMessagePersistenceError(
                "cardshop message registry could not be updated"
            ) from error

    def _initialize_synchronously(self) -> None:
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS cardshop_messages (
                    channel_id TEXT PRIMARY KEY,
                    message_id TEXT NOT NULL
                )
                """
            )

    def _retrieve_message_id_synchronously(self, channel_id: int) -> int | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT message_id FROM cardshop_messages WHERE channel_id = ?",
                (str(channel_id),),
            ).fetchone()
        return int(row[0]) if row is not None else None

    def _store_message_id_synchronously(self, channel_id: int, message_id: int) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO cardshop_messages (channel_id, message_id)
                VALUES (?, ?)
                ON CONFLICT (channel_id) DO UPDATE SET message_id = excluded.message_id
                """,
                (str(channel_id), str(message_id)),
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self._database_path,
            timeout=self._busy_timeout_seconds,
        )
        connection.execute(f"PRAGMA busy_timeout = {round(self._busy_timeout_seconds * 1_000)}")
        return connection


def _validate_snowflake(value: int, name: str) -> None:
    if value <= 0:
        raise ValueError(f"{name} must be positive")
