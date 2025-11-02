# src/core/exceptions.py - Custom exception hierarchy
from typing import Any


class WPChatException(Exception):  # noqa: N818
    """Base exception for wp-chat application"""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for API responses"""
        return {"error": self.__class__.__name__, "message": self.message, "details": self.details}


class DataProcessingError(WPChatException):  # noqa: N818
    """Data fetching/processing errors"""

    pass


class SearchError(WPChatException):  # noqa: N818
    """Search-related errors"""

    pass


class IndexNotFoundError(SearchError):  # noqa: N818
    """FAISS index not found"""

    pass


class GenerationError(WPChatException):  # noqa: N818
    """Generation-related errors"""

    pass


class OpenAIError(GenerationError):  # noqa: N818
    """OpenAI API errors"""

    pass


class ContextTooLargeError(GenerationError):  # noqa: N818
    """Context exceeds token limit"""

    pass


class ConfigurationError(WPChatException):  # noqa: N818
    """Configuration errors"""

    pass


class RateLimitError(WPChatException):  # noqa: N818
    """Rate limit exceeded"""

    pass


class CacheError(WPChatException):  # noqa: N818
    """Cache-related errors"""

    pass


class AuthenticationError(WPChatException):  # noqa: N818
    """Authentication errors"""

    pass


class ValidationError(WPChatException):  # noqa: N818
    """Input validation errors"""

    pass


# HTTP Status Code mapping
EXCEPTION_STATUS_CODE_MAP = {
    DataProcessingError: 502,
    SearchError: 500,
    IndexNotFoundError: 503,
    GenerationError: 500,
    OpenAIError: 503,
    ContextTooLargeError: 413,
    ConfigurationError: 500,
    RateLimitError: 429,
    CacheError: 500,
    AuthenticationError: 401,
    ValidationError: 422,
    WPChatException: 500,  # Default
}


def get_status_code(exception: WPChatException) -> int:
    """Get HTTP status code for exception"""
    return EXCEPTION_STATUS_CODE_MAP.get(type(exception), 500)
