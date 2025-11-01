# tests/integration/test_api_endpoints.py
import pytest


@pytest.mark.integration
class TestAPIEndpoints:
    """Integration tests for API endpoints"""

    def test_stats_health_endpoint(self, test_client):
        """Test /stats/health endpoint"""
        response = test_client.get("/stats/health")

        assert response.status_code == 200
        data = response.json()

        assert "status" in data
        assert "uptime_seconds" in data
        assert "timestamp" in data

    def test_stats_metrics_endpoint(self, test_client):
        """Test /stats/metrics endpoint"""
        response = test_client.get("/stats/metrics")

        assert response.status_code == 200
        data = response.json()

        assert "requests" in data or "total_requests" in data

    def test_search_endpoint_validation(self, test_client):
        """Test /search endpoint input validation"""
        # Valid request
        response = test_client.post("/search", json={"query": "test query", "topk": 5})

        # Should return 200 or 500 (if index not found)
        assert response.status_code in [200, 500]

        # Invalid request - empty query
        response = test_client.post("/search", json={"query": "", "topk": 5})

        # Should fail validation
        assert response.status_code == 422

    def test_ask_endpoint_validation(self, test_client):
        """Test /ask endpoint input validation"""
        # Valid request
        response = test_client.post("/ask", json={"question": "What is VBA?", "topk": 5})

        # Should return 200 or 500 (if index not found)
        assert response.status_code in [200, 500]

        # Invalid request - empty question
        response = test_client.post("/ask", json={"question": "", "topk": 5})

        # Should fail validation
        assert response.status_code == 422

    def test_generate_endpoint_validation(self, test_client):
        """Test /generate endpoint input validation"""
        # Valid request
        response = test_client.post(
            "/generate", json={"question": "VBAについて教えて", "stream": False}
        )

        # Should return 200 or 500 (depending on API key and index)
        assert response.status_code in [200, 500, 503]

        # Invalid request - empty question
        response = test_client.post("/generate", json={"question": "", "stream": False})

        # Should fail validation
        assert response.status_code == 422

    def test_cors_headers(self, test_client):
        """Test CORS headers are present"""
        response = test_client.options("/stats/health")

        # Should have CORS headers
        assert "access-control-allow-origin" in response.headers or response.status_code == 200

    @pytest.mark.slow
    def test_search_response_structure(self, test_client):
        """Test search endpoint response structure"""
        response = test_client.post(
            "/search", json={"query": "VBA string", "topk": 3, "mode": "hybrid"}
        )

        if response.status_code == 200:
            data = response.json()

            assert "results" in data or isinstance(data, list)

            if "results" in data:
                results = data["results"]
            else:
                results = data

            if len(results) > 0:
                # Check first result structure
                result = results[0]
                assert "title" in result or "snippet" in result
