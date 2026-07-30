from typing import Protocol

from kletserbot.domain.cardpacks.pack_configuration import CardSetConfiguration


class CardSetConfigurationProvider(Protocol):
    def retrieve_configurations(self) -> tuple[CardSetConfiguration, ...]: ...
