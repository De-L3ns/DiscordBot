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
