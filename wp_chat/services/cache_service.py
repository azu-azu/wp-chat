"""
Cache Service - Encapsulates caching business logic

This service handles cache operations with:
- Get/set operations
- Cache key generation
- TTL management
- Hit/miss tracking
"""

from ..core.cache import cache_manager, cache_search_results, get_cached_search_results
from ..core.config import get_config_value


class CacheService:
    """Service for handling cache operations"""

    def __init__(self):
        """Initialize cache service"""
        self.cache_manager = cache_manager
        self.enabled = get_config_value("api.cache.enabled", True)
        self.search_ttl = get_config_value("api.cache.search_ttl", 1800)

    def is_enabled(self) -> bool:
        """Check if caching is enabled"""
        return self.enabled

    def get_search_results(self, query: str) -> list | None:
        """
        Get cached search results for a query

        Args:
            query: Search query

        Returns:
            Cached results if found, None otherwise
        """
        if not self.enabled:
            return None

        return get_cached_search_results(query)

    def cache_search_results(self, query: str, results: list, ttl: int | None = None):
        """
        Cache search results

        Args:
            query: Search query
            results: Search results to cache
            ttl: Time to live in seconds (optional, uses default if not provided)
        """
        if not self.enabled:
            return

        ttl = ttl or self.search_ttl
        cache_search_results(query, results, ttl)

    def get_generation_result(self, cache_key: str) -> dict | None:
        """
        Get cached generation result

        Args:
            cache_key: Cache key

        Returns:
            Cached result if found, None otherwise
        """
        if not self.enabled:
            return None

        return self.cache_manager.get(cache_key)

    def cache_generation_result(self, cache_key: str, result: dict, ttl: int | None = None):
        """
        Cache generation result

        Args:
            cache_key: Cache key
            result: Generation result to cache
            ttl: Time to live in seconds (optional, uses default if not provided)
        """
        if not self.enabled:
            return

        ttl = ttl or self.search_ttl
        self.cache_manager.set(cache_key, result, ttl)

    def build_generation_cache_key(self, question: str, topk: int, mode: str, rerank: bool) -> str:
        """
        Build cache key for generation requests

        Args:
            question: User question
            topk: Number of results
            mode: Search mode
            rerank: Whether reranking is enabled

        Returns:
            Cache key string
        """
        return f"generate:{question}:{topk}:{mode}:{rerank}"

    def clear(self) -> bool:
        """
        Clear all cache entries

        Returns:
            True if successful, False otherwise
        """
        return self.cache_manager.clear()

    def get_stats(self) -> dict:
        """
        Get cache statistics

        Returns:
            Dictionary containing cache statistics
        """
        return self.cache_manager.get_stats()
