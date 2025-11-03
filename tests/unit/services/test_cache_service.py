"""
Unit tests for CacheService
"""

from unittest.mock import MagicMock, patch

import pytest

from wp_chat.services.cache_service import CacheService


@pytest.fixture
def mock_cache_manager():
    """Mock cache manager"""
    manager = MagicMock()
    manager.get.return_value = None
    manager.set.return_value = None
    manager.clear.return_value = True
    manager.get_stats.return_value = {"hits": 0, "misses": 0}
    return manager


@pytest.fixture
def mock_config():
    """Mock configuration values"""
    config = {
        "api.cache.enabled": True,
        "api.cache.search_ttl": 1800,
    }

    def get_config_value(key, default=None):
        return config.get(key, default)

    return get_config_value


class TestCacheService:
    """Test suite for CacheService"""

    @patch("wp_chat.services.cache_service.cache_manager")
    @patch("wp_chat.services.cache_service.get_config_value")
    def test_init_default(self, mock_get_config, mock_manager):
        """Test service initialization with default config"""
        mock_get_config.side_effect = lambda key, default: default

        service = CacheService()

        assert service.cache_manager == mock_manager
        assert service.enabled is True
        assert service.search_ttl == 1800

    @patch("wp_chat.services.cache_service.cache_manager")
    @patch("wp_chat.services.cache_service.get_config_value")
    def test_init_custom_config(self, mock_get_config, mock_manager):
        """Test service initialization with custom config"""
        mock_get_config.side_effect = lambda key, default: {
            "api.cache.enabled": False,
            "api.cache.search_ttl": 3600,
        }.get(key, default)

        service = CacheService()

        assert service.enabled is False
        assert service.search_ttl == 3600

    @patch("wp_chat.services.cache_service.cache_manager")
    @patch("wp_chat.services.cache_service.get_config_value")
    def test_is_enabled_true(self, mock_get_config, mock_manager):
        """Test is_enabled when cache is enabled"""
        mock_get_config.side_effect = lambda key, default: True if "enabled" in key else default

        service = CacheService()
        assert service.is_enabled() is True

    @patch("wp_chat.services.cache_service.cache_manager")
    @patch("wp_chat.services.cache_service.get_config_value")
    def test_is_enabled_false(self, mock_get_config, mock_manager):
        """Test is_enabled when cache is disabled"""
        mock_get_config.side_effect = lambda key, default: False if "enabled" in key else default

        service = CacheService()
        assert service.is_enabled() is False

    @patch("wp_chat.services.cache_service.get_cached_search_results")
    @patch("wp_chat.services.cache_service.cache_manager")
    @patch("wp_chat.services.cache_service.get_config_value")
    def test_get_search_results_when_enabled(self, mock_get_config, mock_manager, mock_get_cached):
        """Test getting search results when cache is enabled"""
        mock_get_config.side_effect = lambda key, default: True if "enabled" in key else default
        cached_data = [{"post_id": "1", "score": 0.9}]
        mock_get_cached.return_value = cached_data

        service = CacheService()
        result = service.get_search_results("test query")

        assert result == cached_data
        mock_get_cached.assert_called_once_with("test query")

    @patch("wp_chat.services.cache_service.get_cached_search_results")
    @patch("wp_chat.services.cache_service.cache_manager")
    @patch("wp_chat.services.cache_service.get_config_value")
    def test_get_search_results_when_disabled(self, mock_get_config, mock_manager, mock_get_cached):
        """Test getting search results when cache is disabled"""
        mock_get_config.side_effect = lambda key, default: False if "enabled" in key else default

        service = CacheService()
        result = service.get_search_results("test query")

        assert result is None
        mock_get_cached.assert_not_called()

    @patch("wp_chat.services.cache_service.get_cached_search_results")
    @patch("wp_chat.services.cache_service.cache_manager")
    @patch("wp_chat.services.cache_service.get_config_value")
    def test_get_search_results_cache_miss(self, mock_get_config, mock_manager, mock_get_cached):
        """Test getting search results on cache miss"""
        mock_get_config.side_effect = lambda key, default: True if "enabled" in key else default
        mock_get_cached.return_value = None

        service = CacheService()
        result = service.get_search_results("test query")

        assert result is None

    @patch("wp_chat.services.cache_service.cache_search_results")
    @patch("wp_chat.services.cache_service.cache_manager")
    @patch("wp_chat.services.cache_service.get_config_value")
    def test_cache_search_results_when_enabled(
        self, mock_get_config, mock_manager, mock_cache_func
    ):
        """Test caching search results when cache is enabled"""
        mock_get_config.side_effect = lambda key, default: {
            "api.cache.enabled": True,
            "api.cache.search_ttl": 1800,
        }.get(key, default)

        service = CacheService()
        results = [{"post_id": "1", "score": 0.9}]
        service.cache_search_results("test query", results)

        mock_cache_func.assert_called_once_with("test query", results, 1800)

    @patch("wp_chat.services.cache_service.cache_search_results")
    @patch("wp_chat.services.cache_service.cache_manager")
    @patch("wp_chat.services.cache_service.get_config_value")
    def test_cache_search_results_custom_ttl(self, mock_get_config, mock_manager, mock_cache_func):
        """Test caching search results with custom TTL"""
        mock_get_config.side_effect = lambda key, default: True if "enabled" in key else default

        service = CacheService()
        results = [{"post_id": "1", "score": 0.9}]
        service.cache_search_results("test query", results, ttl=3600)

        mock_cache_func.assert_called_once_with("test query", results, 3600)

    @patch("wp_chat.services.cache_service.cache_search_results")
    @patch("wp_chat.services.cache_service.cache_manager")
    @patch("wp_chat.services.cache_service.get_config_value")
    def test_cache_search_results_when_disabled(
        self, mock_get_config, mock_manager, mock_cache_func
    ):
        """Test caching search results when cache is disabled"""
        mock_get_config.side_effect = lambda key, default: False if "enabled" in key else default

        service = CacheService()
        results = [{"post_id": "1", "score": 0.9}]
        service.cache_search_results("test query", results)

        mock_cache_func.assert_not_called()

    @patch("wp_chat.services.cache_service.cache_manager")
    @patch("wp_chat.services.cache_service.get_config_value")
    def test_get_generation_result_when_enabled(self, mock_get_config, mock_manager):
        """Test getting generation result when cache is enabled"""
        mock_get_config.side_effect = lambda key, default: True if "enabled" in key else default
        cached_data = {"answer": "Test answer", "references": []}
        mock_manager.get.return_value = cached_data

        service = CacheService()
        result = service.get_generation_result("cache_key")

        assert result == cached_data
        mock_manager.get.assert_called_once_with("cache_key")

    @patch("wp_chat.services.cache_service.cache_manager")
    @patch("wp_chat.services.cache_service.get_config_value")
    def test_get_generation_result_when_disabled(self, mock_get_config, mock_manager):
        """Test getting generation result when cache is disabled"""
        mock_get_config.side_effect = lambda key, default: False if "enabled" in key else default

        service = CacheService()
        result = service.get_generation_result("cache_key")

        assert result is None
        mock_manager.get.assert_not_called()

    @patch("wp_chat.services.cache_service.cache_manager")
    @patch("wp_chat.services.cache_service.get_config_value")
    def test_get_generation_result_cache_miss(self, mock_get_config, mock_manager):
        """Test getting generation result on cache miss"""
        mock_get_config.side_effect = lambda key, default: True if "enabled" in key else default
        mock_manager.get.return_value = None

        service = CacheService()
        result = service.get_generation_result("cache_key")

        assert result is None

    @patch("wp_chat.services.cache_service.cache_manager")
    @patch("wp_chat.services.cache_service.get_config_value")
    def test_cache_generation_result_when_enabled(self, mock_get_config, mock_manager):
        """Test caching generation result when cache is enabled"""
        mock_get_config.side_effect = lambda key, default: {
            "api.cache.enabled": True,
            "api.cache.search_ttl": 1800,
        }.get(key, default)

        service = CacheService()
        result = {"answer": "Test answer", "references": []}
        service.cache_generation_result("cache_key", result)

        mock_manager.set.assert_called_once_with("cache_key", result, 1800)

    @patch("wp_chat.services.cache_service.cache_manager")
    @patch("wp_chat.services.cache_service.get_config_value")
    def test_cache_generation_result_custom_ttl(self, mock_get_config, mock_manager):
        """Test caching generation result with custom TTL"""
        mock_get_config.side_effect = lambda key, default: True if "enabled" in key else default

        service = CacheService()
        result = {"answer": "Test answer"}
        service.cache_generation_result("cache_key", result, ttl=7200)

        mock_manager.set.assert_called_once_with("cache_key", result, 7200)

    @patch("wp_chat.services.cache_service.cache_manager")
    @patch("wp_chat.services.cache_service.get_config_value")
    def test_cache_generation_result_when_disabled(self, mock_get_config, mock_manager):
        """Test caching generation result when cache is disabled"""
        mock_get_config.side_effect = lambda key, default: False if "enabled" in key else default

        service = CacheService()
        result = {"answer": "Test answer"}
        service.cache_generation_result("cache_key", result)

        mock_manager.set.assert_not_called()

    @patch("wp_chat.services.cache_service.cache_manager")
    @patch("wp_chat.services.cache_service.get_config_value")
    def test_build_generation_cache_key(self, mock_get_config, mock_manager):
        """Test building generation cache key"""
        mock_get_config.side_effect = lambda key, default: default

        service = CacheService()
        cache_key = service.build_generation_cache_key(
            question="What is WordPress?",
            topk=5,
            mode="hybrid",
            rerank=True,
        )

        assert cache_key == "generate:What is WordPress?:5:hybrid:True"

    @patch("wp_chat.services.cache_service.cache_manager")
    @patch("wp_chat.services.cache_service.get_config_value")
    def test_build_generation_cache_key_variations(self, mock_get_config, mock_manager):
        """Test that different parameters produce different cache keys"""
        mock_get_config.side_effect = lambda key, default: default

        service = CacheService()

        key1 = service.build_generation_cache_key("Q1", 5, "hybrid", True)
        key2 = service.build_generation_cache_key("Q2", 5, "hybrid", True)
        key3 = service.build_generation_cache_key("Q1", 10, "hybrid", True)
        key4 = service.build_generation_cache_key("Q1", 5, "dense", True)
        key5 = service.build_generation_cache_key("Q1", 5, "hybrid", False)

        # All should be different
        keys = {key1, key2, key3, key4, key5}
        assert len(keys) == 5

    @patch("wp_chat.services.cache_service.cache_manager")
    @patch("wp_chat.services.cache_service.get_config_value")
    def test_clear(self, mock_get_config, mock_manager):
        """Test clearing cache"""
        mock_get_config.side_effect = lambda key, default: default
        mock_manager.clear.return_value = True

        service = CacheService()
        result = service.clear()

        assert result is True
        mock_manager.clear.assert_called_once()

    @patch("wp_chat.services.cache_service.cache_manager")
    @patch("wp_chat.services.cache_service.get_config_value")
    def test_clear_failure(self, mock_get_config, mock_manager):
        """Test clearing cache when it fails"""
        mock_get_config.side_effect = lambda key, default: default
        mock_manager.clear.return_value = False

        service = CacheService()
        result = service.clear()

        assert result is False

    @patch("wp_chat.services.cache_service.cache_manager")
    @patch("wp_chat.services.cache_service.get_config_value")
    def test_get_stats(self, mock_get_config, mock_manager):
        """Test getting cache statistics"""
        mock_get_config.side_effect = lambda key, default: default
        stats = {"hits": 100, "misses": 50, "hit_rate": 0.67}
        mock_manager.get_stats.return_value = stats

        service = CacheService()
        result = service.get_stats()

        assert result == stats
        mock_manager.get_stats.assert_called_once()


class TestCacheServiceEdgeCases:
    """Test edge cases for CacheService"""

    @patch("wp_chat.services.cache_service.cache_manager")
    @patch("wp_chat.services.cache_service.get_config_value")
    def test_empty_query(self, mock_get_config, mock_cache_func_module):
        """Test caching with empty query string"""
        mock_get_config.side_effect = lambda key, default: default

        service = CacheService()
        cache_key = service.build_generation_cache_key("", 5, "hybrid", True)
        assert cache_key == "generate::5:hybrid:True"

    @patch("wp_chat.services.cache_service.cache_manager")
    @patch("wp_chat.services.cache_service.get_config_value")
    def test_unicode_query(self, mock_get_config, mock_manager):
        """Test caching with unicode query"""
        mock_get_config.side_effect = lambda key, default: default

        service = CacheService()
        cache_key = service.build_generation_cache_key(
            question="日本語の質問", topk=5, mode="hybrid", rerank=True
        )
        assert "日本語の質問" in cache_key

    @patch("wp_chat.services.cache_service.cache_manager")
    @patch("wp_chat.services.cache_service.get_config_value")
    def test_special_characters_in_query(self, mock_get_config, mock_manager):
        """Test caching with special characters in query"""
        mock_get_config.side_effect = lambda key, default: default

        service = CacheService()
        cache_key = service.build_generation_cache_key(
            question="What is <html>?", topk=5, mode="hybrid", rerank=True
        )
        assert "<html>" in cache_key

    @patch("wp_chat.services.cache_service.cache_manager")
    @patch("wp_chat.services.cache_service.get_config_value")
    def test_zero_topk(self, mock_get_config, mock_manager):
        """Test cache key with zero topk"""
        mock_get_config.side_effect = lambda key, default: default

        service = CacheService()
        cache_key = service.build_generation_cache_key("test", 0, "hybrid", True)
        assert ":0:" in cache_key

    @patch("wp_chat.services.cache_service.cache_manager")
    @patch("wp_chat.services.cache_service.get_config_value")
    def test_large_topk(self, mock_get_config, mock_manager):
        """Test cache key with large topk"""
        mock_get_config.side_effect = lambda key, default: default

        service = CacheService()
        cache_key = service.build_generation_cache_key("test", 1000, "hybrid", True)
        assert ":1000:" in cache_key

    @patch("wp_chat.services.cache_service.cache_search_results")
    @patch("wp_chat.services.cache_service.cache_manager")
    @patch("wp_chat.services.cache_service.get_config_value")
    def test_cache_empty_results(self, mock_get_config, mock_manager, mock_cache_func):
        """Test caching empty results list"""
        mock_get_config.side_effect = lambda key, default: True if "enabled" in key else default

        service = CacheService()
        service.cache_search_results("test", [])

        mock_cache_func.assert_called_once()
        assert mock_cache_func.call_args[0][1] == []

    @patch("wp_chat.services.cache_service.cache_manager")
    @patch("wp_chat.services.cache_service.get_config_value")
    def test_cache_none_result(self, mock_get_config, mock_manager):
        """Test caching None result for generation"""
        mock_get_config.side_effect = lambda key, default: True if "enabled" in key else default

        service = CacheService()
        service.cache_generation_result("key", None)

        # Should still call set even with None
        mock_manager.set.assert_called_once()
        assert mock_manager.set.call_args[0][1] is None

    @patch("wp_chat.services.cache_service.cache_manager")
    @patch("wp_chat.services.cache_service.get_config_value")
    def test_get_stats_empty(self, mock_get_config, mock_manager):
        """Test getting stats when cache is empty"""
        mock_get_config.side_effect = lambda key, default: default
        mock_manager.get_stats.return_value = {}

        service = CacheService()
        result = service.get_stats()

        assert result == {}

    @patch("wp_chat.services.cache_service.cache_manager")
    @patch("wp_chat.services.cache_service.get_config_value")
    def test_ttl_very_short(self, mock_get_config, mock_manager):
        """Test caching with very short TTL"""
        mock_get_config.side_effect = lambda key, default: True if "enabled" in key else default

        service = CacheService()
        service.cache_generation_result("key", {"data": "test"}, ttl=1)

        mock_manager.set.assert_called_once_with("key", {"data": "test"}, 1)
