import asyncio
import json
import os
import re
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import cast

from kletserbot.apps.cardpacks.application.exceptions import CardCatalogUnavailableError
from kletserbot.apps.cardpacks.domain.pokemon_card import PokemonCard
from kletserbot.apps.cardpacks.infrastructure.pokemon_card_payload_mapper import (
    map_complete_payload,
)
from kletserbot.shared.application.exceptions import InvalidExternalResponseError

_SET_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,49}$")


class InvalidPokemonCardCacheError(CardCatalogUnavailableError):
    """Raised when cached or incoming card JSON is malformed."""


class PokemonCardCacheUnavailableError(CardCatalogUnavailableError):
    """Raised when a set has no readable local card cache."""


class JsonPokemonCardCache:
    def __init__(self, cache_directory: Path) -> None:
        self._cache_directory = cache_directory

    async def store_complete_payload(
        self,
        set_id: str,
        payload: Mapping[str, object],
    ) -> None:
        cache_path = self._cache_path(set_id)
        try:
            map_complete_payload(payload)
            await asyncio.to_thread(
                self._store_synchronously,
                cache_path,
                payload,
            )
        except (InvalidExternalResponseError, OSError, TypeError, ValueError) as error:
            raise InvalidPokemonCardCacheError(
                "Pokémon card payload could not be cached"
            ) from error

    async def retrieve_cards(self, set_id: str) -> tuple[PokemonCard, ...]:
        cache_path = self._cache_path(set_id)
        try:
            payload = await asyncio.to_thread(self._read_synchronously, cache_path)
            return map_complete_payload(payload)
        except FileNotFoundError as error:
            raise PokemonCardCacheUnavailableError("cached cards are unavailable") from error
        except (InvalidExternalResponseError, OSError, json.JSONDecodeError) as error:
            raise InvalidPokemonCardCacheError("cached Pokémon cards are invalid") from error

    def _cache_path(self, set_id: str) -> Path:
        if _SET_ID_PATTERN.fullmatch(set_id) is None:
            raise ValueError("set ID contains unsupported characters")
        return self._cache_directory / f"{set_id}.json"

    def _store_synchronously(
        self,
        cache_path: Path,
        payload: Mapping[str, object],
    ) -> None:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=cache_path.parent,
                prefix=f".{cache_path.stem}-",
                suffix=".tmp",
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                json.dump(payload, temporary_file, ensure_ascii=False)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            os.replace(temporary_path, cache_path)
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()

    def _read_synchronously(self, cache_path: Path) -> object:
        with cache_path.open(encoding="utf-8") as cache_file:
            return cast(object, json.load(cache_file))
