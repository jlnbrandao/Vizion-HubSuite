"""Application-wide exceptions mapped later to HTTP status codes.

Keeping them in infrastructure/shared avoids coupling domain to FastAPI/HTTP.
"""

from __future__ import annotations


class ApplicationError(Exception):
    """Base for all application-level errors."""

    def __init__(self, message: str, *, code: str = "application_error") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class NotFoundError(ApplicationError):
    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(message, code="not_found")


class ConflictError(ApplicationError):
    def __init__(self, message: str = "Resource conflict") -> None:
        super().__init__(message, code="conflict")


class ValidationError(ApplicationError):
    def __init__(self, message: str = "Validation failed") -> None:
        super().__init__(message, code="validation_error")


class UnauthorizedError(ApplicationError):
    def __init__(self, message: str = "Unauthorized") -> None:
        super().__init__(message, code="unauthorized")


class ForbiddenError(ApplicationError):
    def __init__(self, message: str = "Forbidden") -> None:
        super().__init__(message, code="forbidden")


class RateLimitExceededError(ApplicationError):
    def __init__(self, message: str = "Too many requests") -> None:
        super().__init__(message, code="rate_limit_exceeded")
