class ApplicationError(Exception):
    """Base class for stable application-level failures."""


class EmptyContentError(ApplicationError):
    """Raised when configured local content is unexpectedly empty."""


class EmptyExternalResultError(ApplicationError):
    """Raised when an external service returns no usable results."""


class ExternalServiceUnavailableError(ApplicationError):
    """Raised when a required external service cannot be reached."""


class InvalidExternalResponseError(ApplicationError):
    """Raised when an external service returns an invalid response."""


class CardpackError(ApplicationError):
    """Base class for stable cardpack feature failures."""


class CardpackConfigurationError(CardpackError):
    """Raised when cardpack configuration files cannot be loaded."""


class CardCatalogUnavailableError(CardpackError):
    """Raised when synchronized or cached Pokémon cards are unavailable."""


class CardpackPersistenceError(CardpackError):
    """Raised when pack inventory persistence fails."""


class CardSetUnavailableError(CardpackError):
    """Raised when a requested card set is not currently usable."""


class InvalidGiftAmountError(CardpackError):
    """Raised when a pack gift amount is outside supported bounds."""


class InsufficientPackInventoryError(CardpackError):
    """Raised when a user no longer owns the pack being opened."""
