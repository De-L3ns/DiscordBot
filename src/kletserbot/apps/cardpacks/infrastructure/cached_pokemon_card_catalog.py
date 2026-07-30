from kletserbot.apps.cardpacks.domain.pokemon_card import PokemonCard
from kletserbot.apps.cardpacks.infrastructure.json_pokemon_card_cache import (
    JsonPokemonCardCache,
)
from kletserbot.apps.cardpacks.infrastructure.pokemon_tcg_client import (
    PokemonTcgClient,
)


class CachedPokemonCardCatalog:
    def __init__(
        self,
        pokemon_tcg_client: PokemonTcgClient,
        card_cache: JsonPokemonCardCache,
    ) -> None:
        self._pokemon_tcg_client = pokemon_tcg_client
        self._card_cache = card_cache

    async def refresh_cards(self, set_id: str) -> tuple[PokemonCard, ...]:
        payload = await self._pokemon_tcg_client.retrieve_complete_set_payload(set_id)
        await self._card_cache.store_complete_payload(set_id, payload)
        return await self._card_cache.retrieve_cards(set_id)

    async def retrieve_cached_cards(
        self,
        set_id: str,
    ) -> tuple[PokemonCard, ...]:
        return await self._card_cache.retrieve_cards(set_id)
