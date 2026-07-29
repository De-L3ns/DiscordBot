import asyncio
from collections.abc import Mapping, Sequence

import aiohttp

from kletserbot.application.exceptions import (
    ExternalServiceUnavailableError,
    InvalidExternalResponseError,
)
from kletserbot.domain.cycling.cycling_leaderboard import CyclingLeaderboard
from kletserbot.domain.cycling.cycling_standing import CyclingStanding
from kletserbot.infrastructure.sporza.indexed_payload_decoder import (
    IndexedPayloadDecoder,
)


class SporzaCyclingClient:
    def __init__(
        self,
        http_session: aiohttp.ClientSession,
        league_url: str,
        payload_decoder: IndexedPayloadDecoder,
        *,
        timeout_seconds: float = 10,
        max_attempts: int = 3,
        retry_delay_seconds: float = 0.25,
    ) -> None:
        self._http_session = http_session
        self._league_url = league_url
        self._payload_decoder = payload_decoder
        self._timeout = aiohttp.ClientTimeout(total=timeout_seconds)
        self._max_attempts = max_attempts
        self._retry_delay_seconds = retry_delay_seconds

    async def retrieve_leaderboard(self) -> CyclingLeaderboard:
        payload = await self._retrieve_payload()
        members = self._extract_members(payload)
        standings = tuple(self._map_standing(member) for member in members)
        if not standings:
            raise InvalidExternalResponseError("Sporza leaderboard contains no teams")
        return CyclingLeaderboard(standings)

    async def _retrieve_payload(self) -> object:
        for attempt in range(1, self._max_attempts + 1):
            try:
                async with self._http_session.get(
                    self._league_url,
                    timeout=self._timeout,
                ) as response:
                    if response.status == 200:
                        try:
                            return await response.json()
                        except ValueError as error:
                            raise InvalidExternalResponseError(
                                "Sporza returned invalid JSON"
                            ) from error
                    if response.status != 429 and response.status < 500:
                        raise InvalidExternalResponseError(
                            f"Sporza returned HTTP {response.status}"
                        )
            except (TimeoutError, aiohttp.ClientError) as error:
                if attempt == self._max_attempts:
                    raise ExternalServiceUnavailableError("Sporza is unavailable") from error

            if attempt < self._max_attempts:
                await asyncio.sleep(self._retry_delay_seconds * attempt)

        raise ExternalServiceUnavailableError("Sporza is unavailable")

    def _extract_members(self, payload: object) -> Sequence[object]:
        if isinstance(payload, list):
            decoded_payload = self._payload_decoder.decode(payload)
            try:
                route_payload = next(iter(decoded_payload.values()))
                if not isinstance(route_payload, Mapping):
                    raise TypeError
                data = route_payload["data"]
                if not isinstance(data, Mapping):
                    raise TypeError
                competition = data["miniCompetition"]
                if not isinstance(competition, Mapping):
                    raise TypeError
                members = competition["members"]
            except (KeyError, StopIteration, TypeError) as error:
                raise InvalidExternalResponseError(
                    "Sporza indexed payload has an invalid structure"
                ) from error
        elif isinstance(payload, Mapping):
            members = payload.get("teams")
        else:
            members = None

        if not isinstance(members, Sequence) or isinstance(
            members,
            (str, bytes, bytearray),
        ):
            raise InvalidExternalResponseError("Sporza leaderboard members must be a list")
        return members

    def _map_standing(self, raw_standing: object) -> CyclingStanding:
        if not isinstance(raw_standing, Mapping):
            raise InvalidExternalResponseError("Sporza team entry must be an object")
        team_name = raw_standing.get("teamName") or raw_standing.get("name")
        rank = raw_standing.get("rank")
        points = raw_standing.get("points")
        if (
            not isinstance(team_name, str)
            or isinstance(rank, bool)
            or not isinstance(rank, int)
            or isinstance(points, bool)
            or not isinstance(points, int)
        ):
            raise InvalidExternalResponseError("Sporza team entry contains invalid values")
        try:
            return CyclingStanding(
                rank=rank,
                team_name=team_name,
                points=points,
            )
        except ValueError as error:
            raise InvalidExternalResponseError(
                "Sporza team entry violates leaderboard rules"
            ) from error
