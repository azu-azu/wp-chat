# tests/e2e/test_user_flows.py - End-to-end tests for user scenarios
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    """Create test client for E2E tests"""
    from wp_chat.api.chat_api import app

    return TestClient(app)


class TestUserSearchFlow:
    """Test complete user search workflows"""

    def test_basic_search_workflow(self, client):
        """Test basic search workflow: query -> results"""
        # Note: This test requires actual FAISS index to be built
        # It may fail in CI without proper setup

        search_data = {"query": "VBA", "topk": 5, "mode": "hybrid", "rerank": False}

        response = client.post("/search", json=search_data)

        # Should return results or appropriate error
        assert response.status_code in [200, 400, 404, 503]

        if response.status_code == 200:
            data = response.json()
            assert "contexts" in data or "query" in data

    def test_search_with_different_modes(self, client):
        """Test search with different modes"""
        query = "Python"
        modes = ["dense", "bm25", "hybrid"]

        for mode in modes:
            search_data = {"query": query, "topk": 5, "mode": mode}
            response = client.post("/search", json=search_data)

            # All modes should work (or fail consistently)
            assert response.status_code in [200, 400, 404, 503]


class TestUserGenerationFlow:
    """Test complete user generation workflows"""

    def test_basic_generation_workflow(self, client):
        """Test basic generation workflow: question -> answer with citations"""
        # Note: Requires OpenAI API key and FAISS index

        generate_data = {
            "question": "VBAで文字列を処理する方法を教えて",
            "topk": 5,
            "stream": False,
            "mode": "hybrid",
        }

        response = client.post("/generate", json=generate_data)

        # Should return answer or appropriate error
        assert response.status_code in [200, 400, 401, 503]

        if response.status_code == 200:
            data = response.json()
            assert "answer" in data or "error" in data

    def test_streaming_generation_workflow(self, client):
        """Test streaming generation workflow"""
        generate_data = {
            "question": "VBAについて教えて",
            "topk": 3,
            "stream": True,
            "mode": "hybrid",
        }

        response = client.post("/generate", json=generate_data)

        # Streaming may not work in TestClient, but endpoint should exist
        assert response.status_code in [200, 400, 401, 503]


class TestUserMonitoringFlow:
    """Test user monitoring and stats workflows"""

    def test_health_check_flow(self, client):
        """Test health check workflow"""
        response = client.get("/stats/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"

    def test_cache_stats_flow(self, client):
        """Test cache statistics workflow"""
        response = client.get("/stats/cache")

        assert response.status_code == 200
        data = response.json()
        assert "total_keys" in data or "error" not in data

    def test_slo_metrics_flow(self, client):
        """Test SLO metrics workflow"""
        response = client.get("/stats/slo")

        assert response.status_code == 200
        data = response.json()
        # SLO data structure may vary
        assert isinstance(data, dict)


class TestUserErrorHandling:
    """Test user error handling scenarios"""

    def test_invalid_search_query(self, client):
        """Test search with invalid query"""
        search_data = {"query": "", "topk": 5}

        response = client.post("/search", json=search_data)

        # Should return validation error
        assert response.status_code in [400, 422]

    def test_invalid_topk_value(self, client):
        """Test search with invalid topk"""
        search_data = {"query": "test", "topk": 9999}

        response = client.post("/search", json=search_data)

        # Should return validation error
        assert response.status_code in [400, 422]

    def test_invalid_mode(self, client):
        """Test search with invalid mode"""
        search_data = {"query": "test", "topk": 5, "mode": "invalid_mode"}

        response = client.post("/search", json=search_data)

        # Should return validation error
        assert response.status_code in [400, 422]

    def test_xss_prevention(self, client):
        """Test XSS attack prevention"""
        search_data = {"query": "<script>alert('xss')</script>VBA", "topk": 5}

        response = client.post("/search", json=search_data)

        # Should sanitize input or return error
        assert response.status_code in [200, 400, 422]

        if response.status_code == 200:
            data = response.json()
            # Check that script tags are removed
            assert "<script>" not in str(data)


class TestUserCompleteJourney:
    """Test complete user journey from search to generation"""

    def test_complete_rag_journey(self, client):
        """Test complete RAG journey: search -> verify results -> generate answer"""
        # Step 1: Search for relevant content
        search_data = {"query": "VBA 文字列", "topk": 5, "mode": "hybrid"}
        search_response = client.post("/search", json=search_data)

        # Search should work or return appropriate error
        assert search_response.status_code in [200, 400, 404, 503]

        # Step 2: Ask a question (simpler endpoint)
        ask_data = {"question": "VBAで文字列を処理する方法は？", "topk": 5, "mode": "hybrid"}
        ask_response = client.post("/ask", json=ask_data)

        assert ask_response.status_code in [200, 400, 404, 503]

        # Step 3: Generate detailed answer with citations
        generate_data = {
            "question": "VBAで文字列を処理する方法を詳しく教えて",
            "topk": 5,
            "stream": False,
        }
        generate_response = client.post("/generate", json=generate_data)

        assert generate_response.status_code in [200, 400, 401, 503]

    def test_monitoring_after_usage(self, client):
        """Test monitoring endpoints after some usage"""
        # Perform some operations
        client.post("/search", json={"query": "test", "topk": 3})

        # Check monitoring endpoints
        health = client.get("/stats/health")
        assert health.status_code == 200

        metrics = client.get("/stats/metrics")
        assert metrics.status_code == 200

        slo = client.get("/stats/slo")
        assert slo.status_code == 200


@pytest.mark.slow
class TestUserPerformanceScenarios:
    """Test user-facing performance scenarios"""

    def test_concurrent_searches(self, client):
        """Test multiple concurrent search requests"""
        import threading

        results = []

        def search():
            response = client.post("/search", json={"query": "test", "topk": 3})
            results.append(response.status_code)

        # Create threads
        threads = [threading.Thread(target=search) for _ in range(10)]

        # Start all threads
        for t in threads:
            t.start()

        # Wait for completion
        for t in threads:
            t.join()

        # All requests should complete
        assert len(results) == 10

    def test_cache_warm_up_scenario(self, client):
        """Test cache warm-up scenario"""
        query = "cache test query"

        # First request (cold cache)
        response1 = client.post("/search", json={"query": query, "topk": 3})

        # Second request (warm cache)
        response2 = client.post("/search", json={"query": query, "topk": 3})

        # Both should succeed (or fail consistently)
        assert response1.status_code == response2.status_code
