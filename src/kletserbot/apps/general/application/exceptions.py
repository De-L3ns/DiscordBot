from kletserbot.shared.application.exceptions import ApplicationError


class EmptyContentError(ApplicationError):
    """Raised when configured local content is unexpectedly empty."""


class EmptyExternalResultError(ApplicationError):
    """Raised when an external service returns no usable results."""
