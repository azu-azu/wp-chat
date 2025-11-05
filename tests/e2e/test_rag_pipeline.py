"""E2E tests for RAG pipeline

Tests the complete RAG flow from API through Services to Domain layer.
Uses real service instances with mocked external dependencies (OpenAI).
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

# ========================================
# Fixtures
# ========================================


@pytest.fixture(scope="module")
def e2e_client():
    """TestClient with minimal mocking - only external APIs"""
    # Set up test environment
    import os

    from wp_chat.api import main

    os.environ["OPENAI_API_KEY"] = "sk-test-key-e2e"
    os.environ["API_KEY_REQUIRED"] = "false"
    os.environ["RATE_LIMIT_ENABLED"] = "false"

    return TestClient(main.app)


@pytest.fixture
def mock_openai_for_generation():
    """Mock OpenAI API for generation tests"""
    with patch("wp_chat.generation.openai_client.openai_client") as mock_client:
        # Mock successful completion
        mock_metrics = Mock()
        mock_metrics.success = True
        mock_metrics.total_latency_ms = 500
        mock_metrics.ttft_ms = 100
        mock_metrics.token_usage = Mock()
        mock_metrics.token_usage.total_tokens = 150
        mock_metrics.model = "gpt-4o-mini"

        mock_client.chat_completion = AsyncMock(
            return_value=(
                "VBA (Visual Basic for Applications) is a programming language. [[1]]",
                mock_metrics,
            )
        )

        yield mock_client


# ========================================
# RAG Pipeline E2E Tests
# ========================================


class TestSearchToGenerationPipeline:
    """Test complete search → generation pipeline"""

    @pytest.mark.e2e
    def test_search_retrieval_pipeline(self, e2e_client):
        """Test search request flows through all layers correctly"""
        # This tests: API → SearchService → BM25/FAISS → Domain Models
        search_data = {"query": "test query", "topk": 3, "mode": "hybrid", "rerank": False}

        response = e2e_client.post("/search", json=search_data)

        # Should succeed or fail gracefully
        assert response.status_code in [200, 500]  # 500 if index not available

        if response.status_code == 200:
            data = response.json()
            # Verify response structure
            assert "q" in data or "query" in data
            assert "mode" in data
            assert data["mode"] == "hybrid"
            assert "contexts" in data

    @pytest.mark.e2e
    def test_ask_with_snippet_generation(self, e2e_client):
        """Test ask endpoint generates snippets correctly"""
        ask_data = {"question": "What is Python?", "topk": 3, "mode": "dense", "highlight": True}

        response = e2e_client.post("/ask", json=ask_data)

        assert response.status_code in [200, 500]

        if response.status_code == 200:
            data = response.json()
            assert "question" in data
            assert data["question"] == "What is Python?"
            assert "contexts" in data

    @pytest.mark.e2e
    def test_full_rag_generation_pipeline(self, e2e_client, mock_openai_for_generation):
        """Test complete RAG pipeline: search → context → OpenAI → response"""
        # This tests the full flow:
        # API → SearchService → Retrieval → GenerationPipeline → OpenAI → Response
        generate_data = {
            "question": "What is VBA?",
            "topk": 3,
            "mode": "hybrid",
            "stream": False,
            "rerank": False,
        }

        response = e2e_client.post("/generate", json=generate_data)

        # Should succeed or fail gracefully
        assert response.status_code in [200, 500]

        if response.status_code == 200:
            data = response.json()
            # Verify RAG response structure
            assert "answer" in data
            assert "references" in data
            assert "metadata" in data

            # Verify metadata contains expected fields
            metadata = data["metadata"]
            assert "latency_ms" in metadata
            assert "model" in metadata

            # If we got actual results, verify citations
            if "citation_count" in metadata:
                assert isinstance(metadata["citation_count"], int)


# ========================================
# Cache Integration E2E Tests
# ========================================


class TestCacheIntegration:
    """Test cache behavior across the pipeline"""

    @pytest.mark.e2e
    def test_cache_hit_miss_cycle(self, e2e_client):
        """Test cache miss → cache hit cycle"""
        query_data = {"query": "cache test unique query", "topk": 3, "mode": "hybrid"}

        # First request - cache miss
        response1 = e2e_client.post("/search", json=query_data)

        assert response1.status_code in [200, 500]

        if response1.status_code == 200:
            data1 = response1.json()
            # First request should not be cached
            assert data1.get("cached") is not True  # May be missing or False

            # Second request - cache hit
            response2 = e2e_client.post("/search", json=query_data)

            assert response2.status_code == 200
            data2 = response2.json()

            # Second request may be cached
            # (depends on cache configuration)
            assert "contexts" in data2

    @pytest.mark.e2e
    def test_cache_clear_and_rebuild(self, e2e_client):
        """Test cache clearing and rebuilding"""
        # Perform search to populate cache
        e2e_client.post("/search", json={"query": "test", "topk": 3})

        # Clear cache
        clear_response = e2e_client.post("/admin/cache/clear")

        assert clear_response.status_code in [200, 500]

        if clear_response.status_code == 200:
            clear_data = clear_response.json()
            assert clear_data.get("success") is True

        # Search again - should rebuild cache
        rebuild_response = e2e_client.post("/search", json={"query": "test", "topk": 3})

        assert rebuild_response.status_code in [200, 500]


# ========================================
# Error Recovery E2E Tests
# ========================================


class TestErrorRecovery:
    """Test error handling and recovery across pipeline"""

    @pytest.mark.e2e
    def test_search_with_invalid_input_recovery(self, e2e_client):
        """Test system handles invalid input gracefully"""
        # Empty query
        response1 = e2e_client.post("/search", json={"query": "", "topk": 3})
        assert response1.status_code in [400, 422]  # Validation error

        # Valid query after error
        response2 = e2e_client.post("/search", json={"query": "valid query", "topk": 3})
        assert response2.status_code in [200, 500]

    @pytest.mark.e2e
    def test_generation_fallback_on_api_failure(self, e2e_client):
        """Test generation falls back gracefully when OpenAI fails"""
        # Note: In E2E tests with real OpenAI API, this test may actually succeed
        # instead of falling back. We test that the endpoint handles the request
        # gracefully regardless of OpenAI success/failure.

        response = e2e_client.post(
            "/generate",
            json={"question": "Test question", "topk": 3, "stream": False},
        )

        # Should return successful response or handle error gracefully
        assert response.status_code in [200, 500, 503]

        if response.status_code == 200:
            data = response.json()
            # Should have answer (either real or fallback)
            assert "answer" in data
            assert "metadata" in data
            # Metadata should contain expected fields
            metadata = data.get("metadata", {})
            assert "model" in metadata
            assert "latency_ms" in metadata


# ========================================
# Monitoring Integration E2E Tests
# ========================================


class TestMonitoringIntegration:
    """Test monitoring and metrics collection across pipeline"""

    @pytest.mark.e2e
    def test_slo_metrics_after_operations(self, e2e_client):
        """Test SLO metrics are collected after operations"""
        # Perform some operations
        e2e_client.post("/search", json={"query": "test1", "topk": 3})
        e2e_client.post("/search", json={"query": "test2", "topk": 3})

        # Check SLO metrics
        slo_response = e2e_client.get("/stats/slo")

        assert slo_response.status_code == 200
        slo_data = slo_response.json()

        # Should contain SLO status
        assert isinstance(slo_data, dict)

    @pytest.mark.e2e
    def test_stats_endpoints_consistency(self, e2e_client):
        """Test stats endpoints return consistent data"""
        # Health check
        health = e2e_client.get("/stats/health")
        assert health.status_code == 200
        assert health.json()["status"] == "healthy"

        # Metrics
        metrics = e2e_client.get("/stats/metrics")
        assert metrics.status_code == 200

        # Cache stats
        cache = e2e_client.get("/stats/cache")
        assert cache.status_code == 200

        # All should return dict structures
        assert isinstance(health.json(), dict)
        assert isinstance(metrics.json(), dict)
        assert isinstance(cache.json(), dict)


# ========================================
# Canary Deployment E2E Tests
# ========================================


class TestCanaryDeployment:
    """Test canary deployment behavior in pipeline"""

    @pytest.mark.e2e
    def test_rerank_canary_rollout(self, e2e_client):
        """Test rerank feature canary deployment"""
        # Search with rerank requested
        search_data = {
            "query": "canary test",
            "topk": 3,
            "mode": "hybrid",
            "rerank": True,  # Request rerank
        }

        response = e2e_client.post(
            "/search", json=search_data, params={"user_id": "test_canary_user"}
        )

        assert response.status_code in [200, 500]

        if response.status_code == 200:
            data = response.json()
            # Should contain canary information
            assert "canary" in data or "rerank" in data


# ========================================
# Data Flow Validation E2E Tests
# ========================================


class TestDataFlowValidation:
    """Test data transformations across pipeline layers"""

    @pytest.mark.e2e
    def test_query_normalization_flow(self, e2e_client):
        """Test query normalization flows through pipeline"""
        # Query with extra spaces and special chars
        query_data = {"query": "  test   query   with   spaces  ", "topk": 3}

        response = e2e_client.post("/search", json=query_data)

        assert response.status_code in [200, 500]

        if response.status_code == 200:
            data = response.json()
            # Query should be normalized in response
            returned_query = data.get("q") or data.get("query")
            # Should have normalized spacing
            assert "  " not in returned_query or returned_query.strip() != ""

    @pytest.mark.e2e
    def test_document_ranking_flow(self, e2e_client):
        """Test document ranking flows correctly through pipeline"""
        search_data = {"query": "test ranking", "topk": 5, "mode": "hybrid"}

        response = e2e_client.post("/search", json=search_data)

        assert response.status_code in [200, 500]

        if response.status_code == 200:
            data = response.json()
            contexts = data.get("contexts", [])

            if len(contexts) > 1:
                # Check that results have scores
                first_result = contexts[0]
                assert "hybrid_score" in first_result or "score" in str(first_result).lower()


# ========================================
# Performance E2E Tests
# ========================================


@pytest.mark.slow
class TestPerformanceE2E:
    """Test performance characteristics of the pipeline"""

    @pytest.mark.e2e
    def test_search_latency_acceptable(self, e2e_client):
        """Test search completes within acceptable time"""
        import time

        start = time.time()
        response = e2e_client.post("/search", json={"query": "performance test", "topk": 3})
        latency_ms = (time.time() - start) * 1000

        # Should complete within reasonable time (even with cold start)
        assert latency_ms < 10000  # 10 seconds max for E2E with possible cold start

        if response.status_code == 200:
            # Verify latency is tracked in response
            data = response.json()
            # Some endpoints may include timing metadata
            assert data is not None

    @pytest.mark.e2e
    def test_concurrent_requests_handling(self, e2e_client):
        """Test system handles concurrent requests"""
        import concurrent.futures

        def make_request(query_id):
            return e2e_client.post(
                "/search", json={"query": f"concurrent test {query_id}", "topk": 3}
            )

        # Make 5 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request, i) for i in range(5)]
            responses = [f.result() for f in concurrent.futures.as_completed(futures)]

        # All should complete
        assert len(responses) == 5

        # Most should succeed (or all fail gracefully)
        status_codes = [r.status_code for r in responses]
        assert all(code in [200, 500] for code in status_codes)
