class ApplicationError(Exception):
    """Base class for stable application-level failures."""


class ExternalServiceUnavailableError(ApplicationError):
    """Raised when a required external service cannot be reached."""


class InvalidExternalResponseError(ApplicationError):
    """Raised when an external service returns an invalid response."""
