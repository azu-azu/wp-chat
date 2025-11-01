# src/core/auth.py - API Key authentication
import os

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

# API Key header configuration
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_api_key(api_key: str | None = Security(API_KEY_HEADER)) -> str | None:
    """
    Verify API key from request header

    Args:
        api_key: API key from X-API-Key header

    Returns:
        API key if valid, None if authentication is disabled

    Raises:
        HTTPException: If API key is required but missing or invalid
    """
    # Check if API key authentication is required
    api_key_required = os.getenv("API_KEY_REQUIRED", "false").lower() == "true"

    if not api_key_required:
        # Authentication is disabled
        return None

    # Get expected API key from environment
    expected_key = os.getenv("API_KEY")

    if not expected_key:
        # API key is required but not configured
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API_KEY not configured on server",
        )

    if not api_key:
        # API key is required but not provided
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if api_key != expected_key:
        # API key is invalid
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return api_key


def verify_api_key(api_key: str) -> bool:
    """
    Verify if API key is valid (for programmatic use)

    Args:
        api_key: API key to verify

    Returns:
        True if valid, False otherwise
    """
    expected_key = os.getenv("API_KEY")

    if not expected_key:
        return False

    return api_key == expected_key


def is_auth_enabled() -> bool:
    """
    Check if API key authentication is enabled

    Returns:
        True if authentication is enabled, False otherwise
    """
    return os.getenv("API_KEY_REQUIRED", "false").lower() == "true"
