import asyncio
import sqlite3
from datetime import date, datetime
from pathlib import Path

from kletserbot.apps.cardpacks.application.cardpack_economy_repository import (
    CardpackEconomyRepository,
)
from kletserbot.apps.cardpacks.application.dto.cardshop_dto import PointMutationResultDto
from kletserbot.apps.cardpacks.application.exceptions import CardpackPersistenceError


class CardpackEconomyPersistenceError(CardpackPersistenceError):
    """Raised when SQLite cannot complete a cardshop economy operation."""


class SqliteCardpackEconomyRepository(CardpackEconomyRepository):
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
            raise CardpackEconomyPersistenceError(
                "cardpack point economy could not be initialized"
            ) from error

    async def retrieve_point_balance(self, discord_user_id: int) -> int:
        _validate_discord_user_id(discord_user_id)
        try:
            return await asyncio.to_thread(
                self._retrieve_point_balance_synchronously,
                discord_user_id,
            )
        except sqlite3.Error as error:
            raise CardpackEconomyPersistenceError(
                "cardpack point balance could not be retrieved"
            ) from error

    async def claim_daily_points(
        self,
        discord_user_id: int,
        claim_date: date,
        points: int,
        created_at_utc: datetime,
    ) -> PointMutationResultDto:
        _validate_discord_user_id(discord_user_id)
        _validate_points(points)
        _validate_timestamp(created_at_utc)
        try:
            return await asyncio.to_thread(
                self._claim_daily_points_synchronously,
                discord_user_id,
                claim_date,
                points,
                created_at_utc,
            )
        except sqlite3.Error as error:
            raise CardpackEconomyPersistenceError(
                "daily cardpack points could not be claimed"
            ) from error

    async def grant_points(
        self,
        discord_user_id: int,
        actor_discord_user_id: int,
        points: int,
        created_at_utc: datetime,
    ) -> int:
        _validate_discord_user_id(discord_user_id)
        _validate_discord_user_id(actor_discord_user_id)
        _validate_points(points)
        _validate_timestamp(created_at_utc)
        try:
            return await asyncio.to_thread(
                self._grant_points_synchronously,
                discord_user_id,
                actor_discord_user_id,
                points,
                created_at_utc,
            )
        except sqlite3.Error as error:
            raise CardpackEconomyPersistenceError("cardpack points could not be granted") from error

    async def purchase_packs(
        self,
        discord_user_id: int,
        set_id: str,
        quantity: int,
        total_price: int,
        created_at_utc: datetime,
    ) -> int | None:
        _validate_discord_user_id(discord_user_id)
        if not set_id:
            raise ValueError("set ID must not be empty")
        _validate_points(quantity)
        _validate_points(total_price)
        _validate_timestamp(created_at_utc)
        try:
            return await asyncio.to_thread(
                self._purchase_packs_synchronously,
                discord_user_id,
                set_id,
                quantity,
                total_price,
                created_at_utc,
            )
        except sqlite3.Error as error:
            raise CardpackEconomyPersistenceError(
                "cardpack purchase could not be completed"
            ) from error

    def _initialize_synchronously(self) -> None:
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS point_accounts (
                    discord_user_id TEXT PRIMARY KEY,
                    balance INTEGER NOT NULL CHECK (balance >= 0),
                    last_daily_claim_date TEXT
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS point_transactions (
                    transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    discord_user_id TEXT NOT NULL,
                    actor_discord_user_id TEXT,
                    transaction_kind TEXT NOT NULL CHECK (
                        transaction_kind IN ('daily_claim', 'admin_grant', 'pack_purchase')
                    ),
                    points_delta INTEGER NOT NULL CHECK (points_delta != 0),
                    set_id TEXT,
                    pack_quantity INTEGER,
                    created_at_utc TEXT NOT NULL
                )
                """
            )

    def _retrieve_point_balance_synchronously(self, discord_user_id: int) -> int:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT balance FROM point_accounts WHERE discord_user_id = ?",
                (str(discord_user_id),),
            ).fetchone()
        return int(row[0]) if row is not None else 0

    def _claim_daily_points_synchronously(
        self,
        discord_user_id: int,
        claim_date: date,
        points: int,
        created_at_utc: datetime,
    ) -> PointMutationResultDto:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            cursor = connection.execute(
                """
                INSERT INTO point_accounts (discord_user_id, balance, last_daily_claim_date)
                VALUES (?, ?, ?)
                ON CONFLICT (discord_user_id) DO UPDATE SET
                    balance = point_accounts.balance + excluded.balance,
                    last_daily_claim_date = excluded.last_daily_claim_date
                WHERE point_accounts.last_daily_claim_date IS NULL
                   OR point_accounts.last_daily_claim_date < excluded.last_daily_claim_date
                """,
                (str(discord_user_id), points, claim_date.isoformat()),
            )
            was_applied = cursor.rowcount == 1
            if was_applied:
                self._insert_transaction(
                    connection,
                    discord_user_id=discord_user_id,
                    actor_discord_user_id=None,
                    transaction_kind="daily_claim",
                    points_delta=points,
                    set_id=None,
                    pack_quantity=None,
                    created_at_utc=created_at_utc,
                )
            balance_row = connection.execute(
                "SELECT balance FROM point_accounts WHERE discord_user_id = ?",
                (str(discord_user_id),),
            ).fetchone()
            connection.commit()
        return PointMutationResultDto(
            was_applied=was_applied,
            point_balance=int(balance_row[0]),
        )

    def _grant_points_synchronously(
        self,
        discord_user_id: int,
        actor_discord_user_id: int,
        points: int,
        created_at_utc: datetime,
    ) -> int:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                INSERT INTO point_accounts (discord_user_id, balance, last_daily_claim_date)
                VALUES (?, ?, NULL)
                ON CONFLICT (discord_user_id)
                DO UPDATE SET balance = point_accounts.balance + excluded.balance
                """,
                (str(discord_user_id), points),
            )
            self._insert_transaction(
                connection,
                discord_user_id=discord_user_id,
                actor_discord_user_id=actor_discord_user_id,
                transaction_kind="admin_grant",
                points_delta=points,
                set_id=None,
                pack_quantity=None,
                created_at_utc=created_at_utc,
            )
            balance_row = connection.execute(
                "SELECT balance FROM point_accounts WHERE discord_user_id = ?",
                (str(discord_user_id),),
            ).fetchone()
            connection.commit()
        return int(balance_row[0])

    def _purchase_packs_synchronously(
        self,
        discord_user_id: int,
        set_id: str,
        quantity: int,
        total_price: int,
        created_at_utc: datetime,
    ) -> int | None:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            cursor = connection.execute(
                """
                UPDATE point_accounts
                SET balance = balance - ?
                WHERE discord_user_id = ? AND balance >= ?
                """,
                (total_price, str(discord_user_id), total_price),
            )
            if cursor.rowcount != 1:
                connection.rollback()
                return None
            connection.execute(
                """
                INSERT INTO pack_inventory (discord_user_id, set_id, quantity)
                VALUES (?, ?, ?)
                ON CONFLICT (discord_user_id, set_id)
                DO UPDATE SET quantity = quantity + excluded.quantity
                """,
                (str(discord_user_id), set_id, quantity),
            )
            self._insert_transaction(
                connection,
                discord_user_id=discord_user_id,
                actor_discord_user_id=discord_user_id,
                transaction_kind="pack_purchase",
                points_delta=-total_price,
                set_id=set_id,
                pack_quantity=quantity,
                created_at_utc=created_at_utc,
            )
            balance_row = connection.execute(
                "SELECT balance FROM point_accounts WHERE discord_user_id = ?",
                (str(discord_user_id),),
            ).fetchone()
            connection.commit()
        return int(balance_row[0])

    @staticmethod
    def _insert_transaction(
        connection: sqlite3.Connection,
        *,
        discord_user_id: int,
        actor_discord_user_id: int | None,
        transaction_kind: str,
        points_delta: int,
        set_id: str | None,
        pack_quantity: int | None,
        created_at_utc: datetime,
    ) -> None:
        connection.execute(
            """
            INSERT INTO point_transactions (
                discord_user_id, actor_discord_user_id, transaction_kind, points_delta,
                set_id, pack_quantity, created_at_utc
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(discord_user_id),
                str(actor_discord_user_id) if actor_discord_user_id is not None else None,
                transaction_kind,
                points_delta,
                set_id,
                pack_quantity,
                created_at_utc.isoformat(),
            ),
        )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self._database_path,
            timeout=self._busy_timeout_seconds,
        )
        connection.execute(f"PRAGMA busy_timeout = {round(self._busy_timeout_seconds * 1_000)}")
        connection.execute("PRAGMA foreign_keys = ON")
        return connection


def _validate_discord_user_id(discord_user_id: int) -> None:
    if discord_user_id <= 0:
        raise ValueError("Discord user ID must be positive")


def _validate_points(points: int) -> None:
    if points <= 0:
        raise ValueError("point amount must be positive")


def _validate_timestamp(created_at_utc: datetime) -> None:
    if created_at_utc.tzinfo is None or created_at_utc.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
