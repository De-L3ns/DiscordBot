import asyncio
import re
from collections.abc import Mapping

import aiohttp

from kletserbot.application.exceptions import (
    ExternalServiceUnavailableError,
    InvalidExternalResponseError,
)
from kletserbot.infrastructure.cardpacks.pokemon_card_payload_mapper import (
    validate_page_payload,
)

_SET_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,49}$")


class PokemonTcgClient:
    _CARD_ENDPOINT = "https://api.pokemontcg.io/v2/cards"

    def __init__(
        self,
        http_session: aiohttp.ClientSession,
        *,
        api_key: str | None,
        timeout_seconds: float = 10,
        max_attempts: int = 3,
        retry_delay_seconds: float = 0.25,
        page_size: int = 250,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout must be positive")
        if not 1 <= max_attempts <= 5:
            raise ValueError("max attempts must be between 1 and 5")
        if retry_delay_seconds < 0:
            raise ValueError("retry delay must not be negative")
        if not 1 <= page_size <= 250:
            raise ValueError("page size must be between 1 and 250")
        self._http_session = http_session
        self._api_key = api_key
        self._timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        self._max_attempts = max_attempts
        self._retry_delay_seconds = retry_delay_seconds
        self._page_size = page_size

    async def retrieve_complete_set_payload(
        self,
        set_id: str,
    ) -> dict[str, object]:
        if _SET_ID_PATTERN.fullmatch(set_id) is None:
            raise ValueError("set ID contains unsupported characters")

        all_cards: list[object] = []
        first_page_payload: dict[str, object] | None = None
        expected_total_count: int | None = None
        page = 1
        while expected_total_count is None or len(all_cards) < expected_total_count:
            page_payload = await self._retrieve_page(set_id=set_id, page=page)
            validated_page = validate_page_payload(
                page_payload,
                expected_page=page,
            )
            raw_cards = validated_page["data"]
            if not isinstance(raw_cards, list):
                raise InvalidExternalResponseError("Pokémon card data must be a list")
            total_count = validated_page["totalCount"]
            if isinstance(total_count, bool) or not isinstance(total_count, int):
                raise InvalidExternalResponseError("Pokémon card totalCount must be an integer")
            if expected_total_count is None:
                expected_total_count = total_count
                first_page_payload = dict(validated_page)
            elif total_count != expected_total_count:
                raise InvalidExternalResponseError(
                    "Pokémon card totalCount changed during pagination"
                )
            if not raw_cards and len(all_cards) < expected_total_count:
                raise InvalidExternalResponseError(
                    "Pokémon card pagination ended before totalCount"
                )
            all_cards.extend(raw_cards)
            if len(all_cards) > expected_total_count:
                raise InvalidExternalResponseError("Pokémon card pagination exceeded totalCount")
            page += 1

        if first_page_payload is None or expected_total_count is None:
            raise InvalidExternalResponseError("Pokémon card response contains no pages")
        first_page_payload["data"] = all_cards
        first_page_payload["page"] = 1
        first_page_payload["pageSize"] = self._page_size
        first_page_payload["count"] = len(all_cards)
        first_page_payload["totalCount"] = expected_total_count
        return first_page_payload

    async def _retrieve_page(
        self,
        *,
        set_id: str,
        page: int,
    ) -> object:
        headers = {}
        if self._api_key is not None:
            headers["X-Api-Key"] = self._api_key
        params: Mapping[str, str | int] = {
            "q": f"set.id:{set_id}",
            "page": page,
            "pageSize": self._page_size,
        }
        for attempt in range(1, self._max_attempts + 1):
            try:
                async with self._http_session.get(
                    self._CARD_ENDPOINT,
                    headers=headers,
                    params=params,
                    timeout=self._timeout,
                ) as response:
                    if response.status == 200:
                        try:
                            return await response.json()
                        except ValueError as error:
                            raise InvalidExternalResponseError(
                                "Pokémon TCG API returned invalid JSON"
                            ) from error
                    if response.status != 429 and response.status < 500:
                        raise InvalidExternalResponseError(
                            f"Pokémon TCG API returned HTTP {response.status}"
                        )
            except (TimeoutError, aiohttp.ClientError) as error:
                if attempt == self._max_attempts:
                    raise ExternalServiceUnavailableError(
                        "Pokémon TCG API is unavailable"
                    ) from error
            if attempt < self._max_attempts:
                await asyncio.sleep(self._retry_delay_seconds * attempt)

        raise ExternalServiceUnavailableError("Pokémon TCG API is unavailable")
