from typing import Protocol

from kletserbot.apps.cardpacks.domain.pack_configuration import CardSetConfiguration


class CardSetConfigurationProvider(Protocol):
    def retrieve_configurations(self) -> tuple[CardSetConfiguration, ...]: ...
