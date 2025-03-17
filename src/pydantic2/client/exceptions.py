from typing import Optional, Any, Dict
from pydantic import BaseModel


class LibraryError(Exception):
    """Base exception for all errors."""
    pass


class BudgetExceeded(LibraryError):
    """Raised when a request would exceed the user's budget limit."""

    def __init__(self, current_cost: float, budget_limit: float):
        self.current_cost = current_cost
        self.budget_limit = budget_limit
        super().__init__(
            f"Budget limit of ${budget_limit:.4f} exceeded (current cost: ${current_cost:.4f})"
        )


class ErrorGeneratingResponse(LibraryError):
    """Raised when an error occurs while generating a response."""

    def __init__(self, message: str, error: Exception, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.error = error
        self.details = details or {}
        super().__init__(f"{message}: {error}")


class ModelNotFound(LibraryError):
    """Raised when the requested model is not found or not available."""

    def __init__(self, model_name: str, provider: Optional[str] = None):
        self.model_name = model_name
        self.provider = provider
        message = f"Model '{model_name}' not found"
        if provider:
            message += f" for provider '{provider}'"
        super().__init__(message)


class InvalidConfiguration(LibraryError):
    """Raised when there's an invalid configuration."""

    def __init__(self, message: str, config_key: Optional[str] = None):
        self.message = message
        self.config_key = config_key
        super_message = message
        if config_key:
            super_message = f"Invalid configuration for '{config_key}': {message}"
        super().__init__(super_message)


class AuthenticationError(LibraryError):
    """Raised when there's an authentication error."""

    def __init__(self, message: str, provider: Optional[str] = None):
        self.message = message
        self.provider = provider
        super_message = message
        if provider:
            super_message = f"Authentication error for provider '{provider}': {message}"
        super().__init__(super_message)


class RateLimitExceeded(LibraryError):
    """Raised when rate limits are exceeded."""

    def __init__(self, message: str, retry_after: Optional[int] = None):
        self.message = message
        self.retry_after = retry_after
        super_message = message
        if retry_after:
            super_message = f"{message} (retry after {retry_after} seconds)"
        super().__init__(super_message)


class ValidationError(LibraryError):
    """Raised when response validation fails."""

    def __init__(self, message: str, model: Optional[BaseModel] = None, errors: Optional[Dict[str, Any]] = None):
        self.message = message
        self.model = model
        self.errors = errors or {}
        super_message = message
        if model:
            super_message = f"Validation error for {model.__class__.__name__}: {message}"
        super().__init__(super_message)


class NetworkError(LibraryError):
    """Raised when there's a network-related error."""

    def __init__(self, message: str, status_code: Optional[int] = None, response: Optional[Any] = None):
        self.message = message
        self.status_code = status_code
        self.response = response
        super_message = message
        if status_code:
            super_message = f"Network error (status {status_code}): {message}"
        super().__init__(super_message)
