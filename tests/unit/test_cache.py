# tests/unit/test_cache.py
import os
import time

import pytest

from src.core.cache import CacheManager


@pytest.mark.unit
class TestCacheManager:
    """Unit tests for CacheManager"""

    def test_cache_initialization(self, temp_cache_dir):
        """Test cache manager initialization"""
        cache = CacheManager(cache_dir=temp_cache_dir, max_size_mb=10)

        assert cache.cache_dir == temp_cache_dir
        assert cache.max_size_mb == 10
        assert os.path.exists(temp_cache_dir)

    def test_cache_set_and_get(self, temp_cache_dir):
        """Test setting and getting cache"""
        cache = CacheManager(cache_dir=temp_cache_dir)

        key = "test_key"
        value = {"data": "test_value", "number": 123}

        # Set cache
        cache.set(key, value, ttl=300)

        # Get cache
        cached_value = cache.get(key)

        assert cached_value == value

    def test_cache_expiration(self, temp_cache_dir):
        """Test cache expiration"""
        cache = CacheManager(cache_dir=temp_cache_dir)

        key = "expiring_key"
        value = "expiring_value"

        # Set with short TTL
        cache.set(key, value, ttl=1)

        # Should exist immediately
        assert cache.get(key) == value

        # Wait for expiration
        time.sleep(1.5)

        # Should be None after expiration
        assert cache.get(key) is None

    def test_cache_miss(self, temp_cache_dir):
        """Test cache miss"""
        cache = CacheManager(cache_dir=temp_cache_dir)

        # Non-existent key
        result = cache.get("non_existent_key")

        assert result is None

    def test_cache_invalidate(self, temp_cache_dir):
        """Test cache invalidation"""
        cache = CacheManager(cache_dir=temp_cache_dir)

        key = "test_key"
        value = "test_value"

        # Set cache
        cache.set(key, value, ttl=300)
        assert cache.get(key) == value

        # Invalidate
        cache.invalidate(key)

        # Should be None after invalidation
        assert cache.get(key) is None

    def test_cache_clear(self, temp_cache_dir):
        """Test clearing all cache"""
        cache = CacheManager(cache_dir=temp_cache_dir)

        # Set multiple cache entries
        cache.set("key1", "value1", ttl=300)
        cache.set("key2", "value2", ttl=300)
        cache.set("key3", "value3", ttl=300)

        # Verify they exist
        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"

        # Clear all
        cache.clear()

        # All should be None
        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert cache.get("key3") is None

    def test_cache_stats(self, temp_cache_dir):
        """Test cache statistics"""
        cache = CacheManager(cache_dir=temp_cache_dir)

        # Set some cache entries
        cache.set("key1", "value1", ttl=300)
        cache.set("key2", "value2", ttl=300)

        # Get stats
        stats = cache.get_stats()

        assert "total_entries" in stats
        assert stats["total_entries"] >= 2
        assert "total_size_bytes" in stats
        assert stats["total_size_bytes"] > 0

    def test_cache_size_limit(self, temp_cache_dir):
        """Test cache size limit enforcement"""
        # Create cache with small limit
        cache = CacheManager(cache_dir=temp_cache_dir, max_size_mb=1)

        # Try to cache large data
        large_data = "x" * 1024 * 1024  # 1MB string

        cache.set("key1", large_data, ttl=300)

        # Should still work but trigger eviction mechanism
        stats = cache.get_stats()
        assert stats["total_size_bytes"] <= cache.max_size_bytes * 1.1  # Allow 10% overflow
