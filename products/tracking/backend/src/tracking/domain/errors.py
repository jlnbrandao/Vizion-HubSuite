"""Tracking domain exceptions — no HTTP types."""


class TrackingError(Exception):
    def __init__(self, message: str, *, code: str = "tracking_error") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class NotFoundError(TrackingError):
    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(message, code="not_found")


class ConflictError(TrackingError):
    def __init__(self, message: str = "Resource conflict") -> None:
        super().__init__(message, code="conflict")


class ValidationError(TrackingError):
    def __init__(self, message: str = "Validation failed") -> None:
        super().__init__(message, code="validation_error")


class UnauthorizedError(TrackingError):
    def __init__(self, message: str = "Unauthorized") -> None:
        super().__init__(message, code="unauthorized")


class ForbiddenError(TrackingError):
    def __init__(self, message: str = "Forbidden") -> None:
        super().__init__(message, code="forbidden")
