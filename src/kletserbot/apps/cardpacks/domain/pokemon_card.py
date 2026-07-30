from dataclasses import dataclass
from urllib.parse import urlparse


class InvalidPokemonCardError(ValueError):
    """Raised when cached Pokémon card fields violate domain invariants."""


@dataclass(frozen=True, slots=True)
class PokemonCard:
    card_id: str
    name: str
    number: str
    rarity: str
    supertype: str
    subtypes: tuple[str, ...]
    small_image_url: str
    large_image_url: str

    def __post_init__(self) -> None:
        for field_name, value in (
            ("card ID", self.card_id),
            ("name", self.name),
            ("number", self.number),
            ("rarity", self.rarity),
            ("supertype", self.supertype),
        ):
            if not value.strip():
                raise InvalidPokemonCardError(f"{field_name} must not be empty")

        if any(not subtype.strip() for subtype in self.subtypes):
            raise InvalidPokemonCardError("subtypes must contain only non-empty values")

        for field_name, image_url in (
            ("small image URL", self.small_image_url),
            ("large image URL", self.large_image_url),
        ):
            parsed_url = urlparse(image_url)
            if parsed_url.scheme != "https" or not parsed_url.hostname:
                raise InvalidPokemonCardError(f"{field_name} must be absolute HTTPS")

    @property
    def is_basic_energy(self) -> bool:
        return self.supertype == "Energy" and "Basic" in self.subtypes
