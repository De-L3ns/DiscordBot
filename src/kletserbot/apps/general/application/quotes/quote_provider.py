from typing import Protocol


class QuoteProvider(Protocol):
    def retrieve_quotes(self) -> tuple[str, ...]: ...
