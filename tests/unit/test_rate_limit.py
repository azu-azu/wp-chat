# tests/unit/test_rate_limit.py - Tests for rate_limit.py
import time
from unittest.mock import Mock

import pytest

from wp_chat.core.rate_limit import RateLimiter, check_rate_limit, get_rate_limit_headers


class TestRateLimiter:
    """Test RateLimiter functionality"""

    def test_initialization(self):
        """Test rate limiter initialization"""
        limiter = RateLimiter()
        assert limiter.rate_limits == {}
        assert limiter.cache_dir is not None

    def test_allow_request_new_client(self):
        """Test allowing request for new client"""
        limiter = RateLimiter()
        client_id = "test_client"

        is_allowed, info = limiter.is_allowed(client_id, max_requests=10, window_seconds=60)

        assert is_allowed is True
        assert info["remaining"] == 9
        assert info["limit"] == 10

    def test_rate_limit_exceeded(self):
        """Test rate limit exceeded"""
        limiter = RateLimiter()
        client_id = "test_client"
        max_requests = 3

        # Make requests up to limit
        for _ in range(max_requests):
            is_allowed, info = limiter.is_allowed(
                client_id, max_requests=max_requests, window_seconds=60
            )
            assert is_allowed is True

        # Next request should be blocked
        is_allowed, info = limiter.is_allowed(
            client_id, max_requests=max_requests, window_seconds=60
        )
        assert is_allowed is False
        assert info["remaining"] == 0

    def test_window_reset(self):
        """Test rate limit window reset"""
        limiter = RateLimiter()
        client_id = "test_client"
        max_requests = 2
        window_seconds = 1  # 1 second window

        # Exhaust limit
        limiter.is_allowed(client_id, max_requests=max_requests, window_seconds=window_seconds)
        limiter.is_allowed(client_id, max_requests=max_requests, window_seconds=window_seconds)

        # Wait for window to reset
        time.sleep(1.1)

        # Should be allowed again
        is_allowed, info = limiter.is_allowed(
            client_id, max_requests=max_requests, window_seconds=window_seconds
        )
        assert is_allowed is True

    def test_multiple_clients(self):
        """Test rate limiting for multiple clients"""
        limiter = RateLimiter()

        is_allowed1, _ = limiter.is_allowed("client1", max_requests=5, window_seconds=60)
        is_allowed2, _ = limiter.is_allowed("client2", max_requests=5, window_seconds=60)

        assert is_allowed1 is True
        assert is_allowed2 is True
        # Both clients should have independent limits

    def test_cleanup_old_entries(self):
        """Test cleanup of old entries"""
        limiter = RateLimiter()

        # Add some old entries
        limiter.is_allowed("old_client", max_requests=10, window_seconds=1)

        # Wait for entries to expire
        time.sleep(1.1)

        # Trigger cleanup by checking again
        limiter.is_allowed("old_client", max_requests=10, window_seconds=1)

        # Old entries should be cleaned up automatically

    def test_get_stats(self):
        """Test getting rate limit statistics"""
        limiter = RateLimiter()

        limiter.is_allowed("client1", max_requests=10, window_seconds=60)
        limiter.is_allowed("client2", max_requests=10, window_seconds=60)

        stats = limiter.get_global_stats()

        assert "total_clients" in stats
        assert stats["total_clients"] == 2


class TestRateLimitHelpers:
    """Test rate limit helper functions"""

    @pytest.fixture
    def mock_request(self):
        """Create a mock FastAPI request"""
        request = Mock()
        request.client.host = "127.0.0.1"
        request.headers = {}
        return request

    def test_check_rate_limit(self, mock_request):
        """Test check_rate_limit helper function"""
        is_allowed, info = check_rate_limit(mock_request, max_requests=10, window_seconds=60)

        assert is_allowed is True
        assert "remaining" in info
        assert "limit" in info

    def test_get_rate_limit_headers(self):
        """Test rate limit header generation"""
        info = {"limit": 10, "remaining": 5, "reset": 1234567890}

        headers = get_rate_limit_headers(info)

        assert "X-RateLimit-Limit" in headers
        assert headers["X-RateLimit-Limit"] == "10"
        assert "X-RateLimit-Remaining" in headers
        assert headers["X-RateLimit-Remaining"] == "5"

    def test_different_client_identification(self):
        """Test client identification from different sources"""
        # Test with IP address
        request1 = Mock()
        request1.client.host = "192.168.1.1"
        request1.headers = {}

        is_allowed1, _ = check_rate_limit(request1, max_requests=5, window_seconds=60)
        assert is_allowed1 is True

        # Test with API key in header
        request2 = Mock()
        request2.client.host = "192.168.1.2"
        request2.headers = {"X-API-Key": "test-key"}

        is_allowed2, _ = check_rate_limit(request2, max_requests=5, window_seconds=60)
        assert is_allowed2 is True
