"""
CacheRepository Interface

Abstract interface for caching operations following the Repository Pattern.
Implementations can use Redis, Memcached, or in-memory caching.
"""

from abc import ABC, abstractmethod
from typing import Any


class CacheRepository(ABC):
    """
    Abstract repository interface for caching operations.

    This interface defines the contract for cache implementations,
    allowing the domain layer to remain independent of specific
    caching technologies (Redis, Memcached, in-memory, etc.).
    """

    @abstractmethod
    def get(self, key: str) -> Any | None:
        """
        Retrieve value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value if found, None otherwise
        """
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """
        Store value in cache.

        Args:
            key: Cache key
            value: Value to cache (must be serializable)
            ttl: Time to live in seconds (None = no expiration)

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """
        Delete value from cache.

        Args:
            key: Cache key

        Returns:
            True if key existed and was deleted, False otherwise
        """
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.

        Args:
            key: Cache key

        Returns:
            True if key exists, False otherwise
        """
        pass

    @abstractmethod
    def clear(self) -> bool:
        """
        Clear all cache entries.

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def get_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dictionary with statistics (hits, misses, size, etc.)
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if cache backend is available.

        Returns:
            True if cache backend is ready
        """
        pass

    def get_or_compute(
        self,
        key: str,
        compute_fn: callable,
        ttl: int | None = None,
    ) -> Any:
        """
        Get value from cache or compute if missing.

        Default implementation using get/set primitives.
        Subclasses can override for optimized implementations.

        Args:
            key: Cache key
            compute_fn: Function to compute value if cache miss
            ttl: Time to live in seconds

        Returns:
            Cached or computed value
        """
        # Try to get from cache
        value = self.get(key)
        if value is not None:
            return value

        # Compute and cache
        value = compute_fn()
        self.set(key, value, ttl)
        return value

    def set_many(self, items: dict[str, Any], ttl: int | None = None) -> bool:
        """
        Store multiple values in cache.

        Default implementation using set primitives.
        Subclasses can override for optimized batch operations.

        Args:
            items: Dictionary of key-value pairs
            ttl: Time to live in seconds

        Returns:
            True if all successful, False otherwise
        """
        results = [self.set(key, value, ttl) for key, value in items.items()]
        return all(results)

    def get_many(self, keys: list[str]) -> dict[str, Any]:
        """
        Retrieve multiple values from cache.

        Default implementation using get primitives.
        Subclasses can override for optimized batch operations.

        Args:
            keys: List of cache keys

        Returns:
            Dictionary of key-value pairs (missing keys excluded)
        """
        result = {}
        for key in keys:
            value = self.get(key)
            if value is not None:
                result[key] = value
        return result

    def delete_many(self, keys: list[str]) -> int:
        """
        Delete multiple values from cache.

        Default implementation using delete primitives.
        Subclasses can override for optimized batch operations.

        Args:
            keys: List of cache keys

        Returns:
            Number of keys actually deleted
        """
        return sum(1 for key in keys if self.delete(key))


class CacheError(Exception):
    """Exception raised when cache operations fail."""

    pass
