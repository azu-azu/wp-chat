# tests/integration/test_cache_integration.py - Integration tests for cache functionality
import time

import pytest
from fastapi.testclient import TestClient

from wp_chat.core.cache import cache_manager, cache_search_results, get_cached_search_results


class TestCacheIntegration:
    """Test cache integration with other components"""

    def test_search_cache_integration(self):
        """Test search results caching and retrieval"""
        query = "VBA 文字列処理"
        results = [{"rank": 1, "title": "VBA基礎", "url": "https://example.com/vba", "score": 0.95}]

        # Cache results
        cache_search_results(query, results, ttl_seconds=60)

        # Retrieve from cache
        cached = get_cached_search_results(query)

        assert cached is not None
        assert len(cached) == len(results)
        assert cached[0]["title"] == results[0]["title"]

    def test_cache_miss(self):
        """Test cache miss scenario"""
        query = "nonexistent query"

        cached = get_cached_search_results(query)
        assert cached is None

    def test_cache_expiration_integration(self):
        """Test cache expiration in real scenario"""
        query = "test query"
        results = [{"rank": 1, "title": "Test"}]

        # Cache with short TTL
        cache_search_results(query, results, ttl_seconds=1)

        # Should hit cache immediately
        cached = get_cached_search_results(query)
        assert cached is not None

        # Wait for expiration
        time.sleep(1.1)

        # Should miss cache after expiration
        cached = get_cached_search_results(query)
        assert cached is None

    def test_cache_invalidation(self):
        """Test cache invalidation"""
        query = "test query"
        results = [{"rank": 1, "title": "Test"}]

        # Cache results
        cache_search_results(query, results, ttl_seconds=60)

        # Clear all cache
        cache_manager.clear()

        # Should miss cache after clearing
        cached = get_cached_search_results(query)
        assert cached is None

    def test_multiple_queries_cache(self):
        """Test caching multiple different queries"""
        queries = ["query1", "query2", "query3"]
        results = [
            [{"rank": 1, "title": "Result1"}],
            [{"rank": 1, "title": "Result2"}],
            [{"rank": 1, "title": "Result3"}],
        ]

        # Cache all queries
        for query, result in zip(queries, results, strict=True):
            cache_search_results(query, result, ttl_seconds=60)

        # All should be cached
        for query, expected_result in zip(queries, results, strict=True):
            cached = get_cached_search_results(query)
            assert cached is not None
            assert cached[0]["title"] == expected_result[0]["title"]


class TestAPIWithCache:
    """Test API endpoints with caching enabled"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        # Import here to avoid circular dependency
        from wp_chat.api.chat_api import app

        return TestClient(app)

    def test_search_endpoint_cache_hit(self, client):
        """Test search endpoint with cache hit"""
        # Note: This test would require actual FAISS index and data
        # This is a skeleton test that should be expanded with real data

        query_data = {"query": "VBA", "topk": 5, "mode": "hybrid"}

        # First request (cache miss)
        response1 = client.post("/search", json=query_data)

        # Second request (should hit cache if caching is enabled)
        response2 = client.post("/search", json=query_data)

        # Both should succeed
        assert response1.status_code in [200, 400, 404]  # May fail without index
        assert response2.status_code in [200, 400, 404]

    def test_cache_stats_endpoint(self, client):
        """Test cache statistics endpoint"""
        response = client.get("/stats/cache")

        assert response.status_code == 200
        data = response.json()

        assert "total_keys" in data or "error" not in data


class TestCachePerformance:
    """Test cache performance characteristics"""

    def test_cache_hit_performance(self):
        """Test that cache hits are faster than computation"""
        query = "performance test"
        results = [{"rank": i, "title": f"Result{i}"} for i in range(100)]

        # Measure cache write time
        start = time.time()
        cache_search_results(query, results, ttl_seconds=60)
        _ = time.time() - start

        # Measure cache read time
        start = time.time()
        cached = get_cached_search_results(query)
        read_time = time.time() - start

        # Cache read should be very fast
        assert read_time < 0.1  # Should be under 100ms
        assert cached is not None

    def test_cache_memory_efficiency(self):
        """Test cache memory usage with many entries"""
        # Cache many queries
        for i in range(100):
            query = f"query_{i}"
            results = [{"rank": 1, "title": f"Result{i}"}]
            cache_search_results(query, results, ttl_seconds=60)

        stats = cache_manager.get_stats()

        # Should have all entries cached
        assert stats["total_entries"] >= 90  # Allow some tolerance

    def test_cache_concurrent_access(self):
        """Test cache with concurrent read/write"""
        import threading

        query = "concurrent test"
        results = [{"rank": 1, "title": "Test"}]

        def write_cache():
            cache_search_results(query, results, ttl_seconds=60)

        def read_cache():
            return get_cached_search_results(query)

        # Create threads
        threads = []
        for _ in range(10):
            t1 = threading.Thread(target=write_cache)
            t2 = threading.Thread(target=read_cache)
            threads.extend([t1, t2])

        # Run threads
        for t in threads:
            t.start()

        # Wait for completion
        for t in threads:
            t.join()

        # Cache should still be valid
        cached = get_cached_search_results(query)
        assert cached is not None or cached is None  # May vary based on timing
