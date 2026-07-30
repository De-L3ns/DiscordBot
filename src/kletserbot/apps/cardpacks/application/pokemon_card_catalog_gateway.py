from typing import Protocol

from kletserbot.apps.cardpacks.domain.pokemon_card import PokemonCard


class PokemonCardCatalogGateway(Protocol):
    async def refresh_cards(self, set_id: str) -> tuple[PokemonCard, ...]: ...

    async def retrieve_cached_cards(
        self,
        set_id: str,
    ) -> tuple[PokemonCard, ...]: ...
