"""
Custom exceptions for ServiceNow connectors.
"""


class ServiceNowException(Exception):
    """Base exception for ServiceNow connector errors."""
    pass


class ConnectionError(ServiceNowException):
    """Raised when connection to ServiceNow fails."""
    pass


class AuthenticationError(ServiceNowException):
    """Raised when authentication fails."""
    pass


class APIError(ServiceNowException):
    """Raised when API request fails."""
    pass


class RateLimitError(APIError):
    """Raised when API rate limit is exceeded."""
    pass
