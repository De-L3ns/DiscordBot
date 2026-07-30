from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class QuoteDto:
    text: str
