from collections.abc import Sequence

import pytest

from kletserbot.application.exceptions import EmptyContentError
from kletserbot.application.quotes.quote_service import QuoteService


class FakeQuoteProvider:
    def __init__(self, quotes: tuple[str, ...]) -> None:
        self._quotes = quotes

    def retrieve_quotes(self) -> tuple[str, ...]:
        return self._quotes


def select_last(values: Sequence[str]) -> str:
    return values[-1]


def test_quote_service_returns_selected_quote() -> None:
    service = QuoteService(FakeQuoteProvider(("First", "Second")), select_last)

    assert service.retrieve_quote().text == "Second"


def test_quote_service_rejects_empty_collection() -> None:
    service = QuoteService(FakeQuoteProvider(()), select_last)

    with pytest.raises(EmptyContentError):
        service.retrieve_quote()
