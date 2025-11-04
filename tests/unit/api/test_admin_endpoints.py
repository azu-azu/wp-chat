"""Unit tests for admin and stats API endpoints

Tests the /stats/* and /admin/* endpoints with mocked dependencies.
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

# ========================================
# Fixtures
# ========================================


@pytest.fixture
def admin_test_client():
    """FastAPI TestClient for admin endpoints"""
    from wp_chat.api import main

    client = TestClient(main.app)
    yield client


# ========================================
# Tests for /stats endpoints
# ========================================


class TestStatsEndpoints:
    """Tests for /stats/* GET endpoints"""

    def test_health_check(self, admin_test_client):
        """Test /stats/health endpoint"""
        response = admin_test_client.get("/stats/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data

    @patch("wp_chat.api.routers.stats.get_ab_stats")
    def test_ab_statistics(self, mock_get_ab_stats, admin_test_client):
        """Test /stats/ab endpoint"""
        mock_get_ab_stats.return_value = {
            "total_searches": 100,
            "rerank_enabled": 50,
            "rerank_disabled": 50,
        }

        response = admin_test_client.get("/stats/ab?days=7")

        assert response.status_code == 200
        data = response.json()
        assert data["total_searches"] == 100
        mock_get_ab_stats.assert_called_once_with(7)

    @patch("wp_chat.api.routers.stats.cache_manager")
    def test_cache_stats(self, mock_cache_manager, admin_test_client):
        """Test /stats/cache endpoint"""
        mock_cache_manager.get_stats.return_value = {
            "total_keys": 42,
            "total_size_mb": 15.3,
            "hit_rate": 0.85,
        }

        response = admin_test_client.get("/stats/cache")

        assert response.status_code == 200
        data = response.json()
        assert data["total_keys"] == 42
        assert data["hit_rate"] == 0.85

    @patch("wp_chat.api.routers.stats.cache_manager")
    def test_cache_stats_error_handling(self, mock_cache_manager, admin_test_client):
        """Test /stats/cache error handling"""
        mock_cache_manager.get_stats.side_effect = Exception("Cache error")

        response = admin_test_client.get("/stats/cache")

        assert response.status_code == 500
        data = response.json()
        assert "error" in data

    @patch("wp_chat.api.routers.stats.rate_limiter")
    def test_rate_limit_stats(self, mock_rate_limiter, admin_test_client):
        """Test /stats/rate-limit endpoint"""
        mock_rate_limiter.get_global_stats.return_value = {
            "total_requests": 1000,
            "blocked_requests": 5,
            "active_users": 50,
        }

        response = admin_test_client.get("/stats/rate-limit")

        assert response.status_code == 200
        data = response.json()
        assert data["total_requests"] == 1000
        assert data["blocked_requests"] == 5

    @patch("wp_chat.api.routers.stats.get_slo_status")
    def test_slo_statistics(self, mock_get_slo_status, admin_test_client):
        """Test /stats/slo endpoint"""
        mock_get_slo_status.return_value = {
            "search_availability": 0.999,
            "search_latency_p95": 150,
            "generate_availability": 0.995,
            "generate_latency_p95": 500,
        }

        response = admin_test_client.get("/stats/slo")

        assert response.status_code == 200
        data = response.json()
        assert data["search_availability"] == 0.999
        assert data["search_latency_p95"] == 150

    @patch("wp_chat.api.routers.stats.get_metrics_summary")
    def test_metrics_statistics(self, mock_get_metrics_summary, admin_test_client):
        """Test /stats/metrics endpoint"""
        mock_get_metrics_summary.return_value = {
            "total_requests": 500,
            "avg_latency_ms": 120,
            "error_rate": 0.01,
        }

        response = admin_test_client.get("/stats/metrics?hours=24")

        assert response.status_code == 200
        data = response.json()
        assert data["total_requests"] == 500
        mock_get_metrics_summary.assert_called_once_with(24)

    @patch("wp_chat.api.routers.stats.get_device_status")
    def test_device_status(self, mock_get_device_status, admin_test_client):
        """Test /stats/device endpoint"""
        mock_get_device_status.return_value = {
            "device": "mps",
            "model_name": "all-MiniLM-L6-v2",
            "available_memory_mb": 8192,
        }

        response = admin_test_client.get("/stats/device")

        assert response.status_code == 200
        data = response.json()
        assert data["device"] == "mps"
        assert "model_name" in data

    @patch("wp_chat.api.routers.stats.get_highlight_info")
    def test_highlight_info(self, mock_get_highlight_info, admin_test_client):
        """Test /stats/highlight endpoint"""
        mock_get_highlight_info.return_value = {
            "morphology_available": True,
            "extracted_keywords": ["VBA", "string"],
            "morphology_keywords": ["vba", "string"],
            "basic_keywords": ["VBA", "string"],
        }

        response = admin_test_client.get("/stats/highlight?query=VBA+string")

        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "VBA string"
        assert data["morphology_available"] is True
        assert len(data["extracted_keywords"]) == 2


# ========================================
# Tests for /admin/cache endpoints
# ========================================


class TestAdminCacheEndpoints:
    """Tests for /admin/cache/* POST endpoints"""

    @patch("wp_chat.api.routers.admin_cache.cache_manager")
    def test_clear_cache_success(self, mock_cache_manager, admin_test_client):
        """Test /admin/cache/clear endpoint (success)"""
        mock_cache_manager.clear.return_value = True

        response = admin_test_client.post("/admin/cache/clear")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "message" in data
        mock_cache_manager.clear.assert_called_once()

    @patch("wp_chat.api.routers.admin_cache.cache_manager")
    def test_clear_cache_error(self, mock_cache_manager, admin_test_client):
        """Test /admin/cache/clear endpoint (error)"""
        mock_cache_manager.clear.side_effect = Exception("Cache clear failed")

        response = admin_test_client.post("/admin/cache/clear")

        assert response.status_code == 500
        data = response.json()
        assert "error" in data


# ========================================
# Tests for dashboard endpoints
# ========================================


class TestDashboardEndpoints:
    """Tests for dashboard summary endpoints"""

    @patch("wp_chat.api.routers.stats.get_dashboard_data")
    def test_dashboard_data(self, mock_get_dashboard_data, admin_test_client):
        """Test /stats/dashboard endpoint"""
        mock_get_dashboard_data.return_value = {
            "ab_summary": {},
            "cache_summary": {},
            "performance_summary": {},
            "slo_status": {},
        }

        response = admin_test_client.get("/stats/dashboard?days=7&hours=24")

        assert response.status_code == 200
        data = response.json()
        assert "ab_summary" in data
        assert "cache_summary" in data
        mock_get_dashboard_data.assert_called_once_with(7, 24)

    @patch("wp_chat.api.routers.stats.get_ab_summary")
    def test_ab_summary(self, mock_get_ab_summary, admin_test_client):
        """Test /stats/ab-summary endpoint"""
        mock_get_ab_summary.return_value = {
            "total_queries": 1000,
            "rerank_performance": {"avg_latency": 200},
        }

        response = admin_test_client.get("/stats/ab-summary?days=7")

        assert response.status_code == 200
        data = response.json()
        assert data["total_queries"] == 1000
        mock_get_ab_summary.assert_called_once_with(7)

    @patch("wp_chat.api.routers.stats.get_cache_summary")
    def test_cache_summary(self, mock_get_cache_summary, admin_test_client):
        """Test /stats/cache-summary endpoint"""
        mock_get_cache_summary.return_value = {"hit_rate": 0.85, "total_hits": 500}

        response = admin_test_client.get("/stats/cache-summary?hours=24")

        assert response.status_code == 200
        data = response.json()
        assert data["hit_rate"] == 0.85
        mock_get_cache_summary.assert_called_once_with(24)

    @patch("wp_chat.api.routers.stats.get_performance_summary")
    def test_performance_summary(self, mock_get_performance_summary, admin_test_client):
        """Test /stats/performance-summary endpoint"""
        mock_get_performance_summary.return_value = {
            "avg_latency": 150,
            "p95_latency": 300,
            "p99_latency": 500,
        }

        response = admin_test_client.get("/stats/performance-summary?hours=24")

        assert response.status_code == 200
        data = response.json()
        assert data["avg_latency"] == 150
        assert data["p95_latency"] == 300
        mock_get_performance_summary.assert_called_once_with(24)
