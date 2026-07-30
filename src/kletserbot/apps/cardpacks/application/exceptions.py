from kletserbot.shared.application.exceptions import ApplicationError


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
