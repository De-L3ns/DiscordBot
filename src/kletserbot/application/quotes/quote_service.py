from collections.abc import Callable, Sequence

from kletserbot.application.exceptions import EmptyContentError
from kletserbot.application.quotes.dto.quote_dto import QuoteDto
from kletserbot.application.quotes.quote_provider import QuoteProvider

QuoteSelector = Callable[[Sequence[str]], str]


class QuoteService:
    def __init__(
        self,
        quote_provider: QuoteProvider,
        quote_selector: QuoteSelector,
    ) -> None:
        self._quote_provider = quote_provider
        self._quote_selector = quote_selector

    def retrieve_quote(self) -> QuoteDto:
        quotes = self._quote_provider.retrieve_quotes()
        if not quotes:
            raise EmptyContentError("No quotes are configured")
        return QuoteDto(text=self._quote_selector(quotes))
