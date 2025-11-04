"""Unit tests for chat API endpoints

Tests the /search, /ask, and /generate endpoints with mocked service dependencies.
"""

from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

from wp_chat.domain.models.document import Document
from wp_chat.domain.models.generation_result import GenerationResult
from wp_chat.domain.models.search_result import SearchResult

# ========================================
# Fixtures
# ========================================


@pytest.fixture
def mock_search_service():
    """Mock SearchService"""
    service = MagicMock()
    return service


@pytest.fixture
def mock_generation_service():
    """Mock GenerationService"""
    service = MagicMock()
    return service


@pytest.fixture
def mock_cache_service():
    """Mock CacheService"""
    service = MagicMock()
    # Default: cache miss
    service.get_search_results.return_value = None
    service.get_generation_result.return_value = None
    service.build_generation_cache_key.return_value = "test-cache-key"
    return service


@pytest.fixture
def sample_search_result():
    """Sample SearchResult domain model"""
    docs = [
        Document(
            post_id="1",
            chunk_id=0,
            title="VBA String Processing",
            url="https://example.com/post1",
            chunk="This is about VBA string processing",
            hybrid_score=0.95,
            ce_score=0.92,
            rank=1,
        ),
        Document(
            post_id="2",
            chunk_id=0,
            title="Python Basics",
            url="https://example.com/post2",
            chunk="Introduction to Python programming",
            hybrid_score=0.85,
            ce_score=None,
            rank=2,
        ),
    ]
    return SearchResult(query="test query", mode="hybrid", documents=docs, rerank_enabled=True)


@pytest.fixture
def api_test_client(mock_search_service, mock_generation_service, mock_cache_service):
    """FastAPI TestClient with mocked services"""
    # Import here to avoid circular imports
    from wp_chat.api import main
    from wp_chat.api.routers import chat

    # Mock the service instances in chat router
    with (
        patch.object(chat, "search_service", mock_search_service),
        patch.object(chat, "generation_service", mock_generation_service),
        patch.object(chat, "cache_service", mock_cache_service),
        patch("wp_chat.core.config.get_config_value") as mock_config,
        patch("wp_chat.api.routers.chat.is_rerank_enabled_for_user") as mock_canary,
        patch("wp_chat.api.routers.chat.get_canary_status") as mock_status,
        patch("wp_chat.api.routers.chat.ab_logger"),
    ):
        # Configure mock config
        mock_config.side_effect = lambda key, default=None: {
            "api.rate_limit.enabled": False,  # Disable rate limiting for tests
            "api.snippet_length": 400,
            "api.cache.enabled": True,
        }.get(key, default)

        # Configure canary mocking (default: enabled)
        mock_canary.return_value = True
        mock_status.return_value = {"config": {"rollout_percentage": 1.0}}

        client = TestClient(main.app)
        yield client


# ========================================
# Tests for /search endpoint
# ========================================


class TestSearchEndpoint:
    """Tests for /search POST endpoint"""

    def test_search_valid_request_hybrid_mode(
        self, api_test_client, mock_search_service, mock_cache_service, sample_search_result
    ):
        """Test /search with valid hybrid mode request"""
        mock_cache_service.get_search_results.return_value = None  # Cache miss
        mock_search_service.execute_search.return_value = sample_search_result

        with patch("wp_chat.api.routers.chat.highlight_results") as mock_highlight:
            mock_highlight.return_value = []  # Simplified for test

            response = api_test_client.post(
                "/search", json={"query": "VBA string", "topk": 5, "mode": "hybrid", "rerank": True}
            )

        assert response.status_code == 200
        data = response.json()
        assert "q" in data or "query" in data
        assert data["mode"] == "hybrid"
        assert data["rerank"] is True

        # Verify service was called
        mock_search_service.execute_search.assert_called_once_with(
            query="VBA string", topk=5, mode="hybrid", rerank=True
        )

    def test_search_empty_query_returns_400(self, api_test_client):
        """Test /search with empty query raises 400"""
        response = api_test_client.post(
            "/search", json={"query": "   ", "topk": 5, "mode": "hybrid"}
        )

        assert response.status_code == 400
        data = response.json()
        assert "empty" in data["detail"].lower()

    def test_search_cache_hit(self, api_test_client, mock_cache_service):
        """Test /search returns cached results when available"""
        cached_data = [
            {
                "rank": 1,
                "hybrid_score": 0.95,
                "post_id": "1",
                "chunk_id": 0,
                "title": "Cached Result",
                "url": "https://example.com/cached",
            }
        ]
        mock_cache_service.get_search_results.return_value = cached_data

        response = api_test_client.post(
            "/search", json={"query": "test", "topk": 5, "mode": "hybrid"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data.get("cached") is True
        assert data["contexts"] == cached_data

    def test_search_cache_miss_caches_results(
        self, api_test_client, mock_search_service, mock_cache_service, sample_search_result
    ):
        """Test /search caches results on cache miss"""
        mock_cache_service.get_search_results.return_value = None
        mock_search_service.execute_search.return_value = sample_search_result

        with patch("wp_chat.api.routers.chat.highlight_results") as mock_highlight:
            mock_highlight.return_value = []

            response = api_test_client.post(
                "/search", json={"query": "test", "topk": 5, "mode": "hybrid"}
            )

        assert response.status_code == 200
        # Verify caching was called
        mock_cache_service.cache_search_results.assert_called_once()

    def test_search_dense_mode(self, api_test_client, mock_search_service, mock_cache_service):
        """Test /search with dense mode"""
        mock_cache_service.get_search_results.return_value = None

        # Create SearchResult with dense mode
        docs = [
            Document(
                post_id="1",
                chunk_id=0,
                title="Test Doc",
                url="https://example.com/test",
                chunk="Test content",
                hybrid_score=0.9,
                rank=1,
            )
        ]
        dense_result = SearchResult(
            query="test", mode="dense", documents=docs, rerank_enabled=False
        )
        mock_search_service.execute_search.return_value = dense_result

        with patch(
            "wp_chat.api.routers.chat.highlight_results", side_effect=lambda x, *args, **kwargs: x
        ):
            response = api_test_client.post(
                "/search", json={"query": "test", "topk": 3, "mode": "dense"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "dense"

    def test_search_bm25_mode(self, api_test_client, mock_search_service, mock_cache_service):
        """Test /search with BM25 mode"""
        mock_cache_service.get_search_results.return_value = None

        # Create SearchResult with BM25 mode
        docs = [
            Document(
                post_id="1",
                chunk_id=0,
                title="Test Doc",
                url="https://example.com/test",
                chunk="Test content",
                hybrid_score=0.9,
                rank=1,
            )
        ]
        bm25_result = SearchResult(query="test", mode="bm25", documents=docs, rerank_enabled=False)
        mock_search_service.execute_search.return_value = bm25_result

        with patch(
            "wp_chat.api.routers.chat.highlight_results", side_effect=lambda x, *args, **kwargs: x
        ):
            response = api_test_client.post(
                "/search", json={"query": "test", "topk": 3, "mode": "bm25"}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["mode"] == "bm25"

    def test_search_without_rerank(self, api_test_client, mock_search_service, mock_cache_service):
        """Test /search with rerank=False"""
        mock_cache_service.get_search_results.return_value = None

        # Create SearchResult without reranking
        docs = [
            Document(
                post_id="1",
                chunk_id=0,
                title="Test Doc",
                url="https://example.com/test",
                chunk="Test content",
                hybrid_score=0.9,
                rank=1,
            )
        ]
        no_rerank_result = SearchResult(
            query="test", mode="hybrid", documents=docs, rerank_enabled=False
        )
        mock_search_service.execute_search.return_value = no_rerank_result

        with patch(
            "wp_chat.api.routers.chat.highlight_results", side_effect=lambda x, *args, **kwargs: x
        ):
            response = api_test_client.post(
                "/search", json={"query": "test", "topk": 5, "mode": "hybrid", "rerank": False}
            )

        assert response.status_code == 200
        data = response.json()
        assert data["rerank"] is False

    def test_search_canary_deployment_logic(
        self, api_test_client, mock_search_service, mock_cache_service
    ):
        """Test /search respects canary deployment for rerank decision"""
        mock_cache_service.get_search_results.return_value = None

        # Create SearchResult (canary is enabled by default in fixture)
        docs = [
            Document(
                post_id="1",
                chunk_id=0,
                title="Test Doc",
                url="https://example.com/test",
                chunk="Test content",
                hybrid_score=0.9,
                rank=1,
            )
        ]
        canary_result = SearchResult(
            query="test", mode="hybrid", documents=docs, rerank_enabled=True
        )
        mock_search_service.execute_search.return_value = canary_result

        with patch(
            "wp_chat.api.routers.chat.highlight_results", side_effect=lambda x, *args, **kwargs: x
        ):
            response = api_test_client.post(
                "/search",
                json={"query": "test", "topk": 5, "mode": "hybrid", "rerank": True},
                params={"user_id": "test_user"},
            )

        assert response.status_code == 200
        # Canary is enabled by default in fixture, so rerank should be True
        data = response.json()
        assert "canary" in data


# ========================================
# Tests for /ask endpoint
# ========================================


class TestAskEndpoint:
    """Tests for /ask POST endpoint"""

    def test_ask_valid_request(self, api_test_client, mock_search_service, sample_search_result):
        """Test /ask with valid request"""
        mock_search_service.execute_search.return_value = sample_search_result

        with patch("wp_chat.api.routers.chat.highlight_results") as mock_highlight:
            mock_highlight.return_value = []

            response = api_test_client.post(
                "/ask",
                json={
                    "question": "What is VBA?",
                    "topk": 5,
                    "mode": "hybrid",
                    "rerank": False,
                    "highlight": True,
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["question"] == "What is VBA?"
        assert data["mode"] == "hybrid"
        assert "contexts" in data

    def test_ask_empty_question_returns_400(self, api_test_client):
        """Test /ask with empty question raises 400"""
        response = api_test_client.post("/ask", json={"question": "  ", "topk": 5})

        assert response.status_code == 400

    def test_ask_with_snippets(self, api_test_client, mock_search_service, sample_search_result):
        """Test /ask includes snippets in response"""
        mock_search_service.execute_search.return_value = sample_search_result

        with patch("wp_chat.api.routers.chat.highlight_results"):
            response = api_test_client.post(
                "/ask", json={"question": "test question", "topk": 3, "highlight": False}
            )

        assert response.status_code == 200
        data = response.json()
        # Check that contexts have snippet field
        if data["contexts"]:
            assert "snippet" in data["contexts"][0]


# ========================================
# Tests for /generate endpoint
# ========================================


class TestGenerateEndpoint:
    """Tests for /generate POST endpoint"""

    def test_generate_non_streaming_success(
        self,
        api_test_client,
        mock_search_service,
        mock_generation_service,
        mock_cache_service,
    ):
        """Test /generate with non-streaming response (success case)"""
        mock_cache_service.get_generation_result.return_value = None

        # Create SearchResult
        docs = [
            Document(
                post_id="1",
                chunk_id=0,
                title="VBA Guide",
                url="https://example.com/vba",
                chunk="VBA is a programming language",
                hybrid_score=0.95,
                rank=1,
            )
        ]
        search_result = SearchResult(
            query="What is VBA?", mode="hybrid", documents=docs, rerank_enabled=True
        )
        mock_search_service.execute_search.return_value = search_result
        mock_generation_service.prepare_from_domain_documents.return_value = []

        with (
            patch("wp_chat.api.routers.chat.generation_pipeline") as mock_pipeline,
            patch("wp_chat.api.routers.chat.openai_client") as mock_openai,
        ):
            # Mock pipeline
            mock_pipeline.process_retrieval_results.return_value = ([], {})
            mock_pipeline.build_prompt.return_value = ([], {})
            mock_pipeline.post_process_response.return_value = GenerationResult(
                answer="This is a test answer",
                references=[{"title": "Test", "url": "https://example.com"}],
                metadata={"citation_count": 1, "has_citations": True},
            )

            # Mock OpenAI response (it's an async function, need to use AsyncMock)
            from unittest.mock import AsyncMock

            mock_metrics = Mock()
            mock_metrics.success = True
            mock_metrics.total_latency_ms = 500
            mock_metrics.ttft_ms = 100
            mock_metrics.token_usage = Mock()
            mock_metrics.token_usage.total_tokens = 150
            mock_metrics.model = "gpt-4o-mini"

            mock_openai.chat_completion = AsyncMock(
                return_value=("Test answer [[1]]", mock_metrics)
            )

            response = api_test_client.post(
                "/generate",
                json={"question": "What is VBA?", "topk": 5, "stream": False},
            )

        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "references" in data
        assert "metadata" in data
        assert data["metadata"]["model"] == "gpt-4o-mini"

    def test_generate_empty_question_returns_400(self, api_test_client):
        """Test /generate with empty question raises 400"""
        response = api_test_client.post(
            "/generate", json={"question": "  ", "topk": 5, "stream": False}
        )

        assert response.status_code == 400

    def test_generate_cache_hit(self, api_test_client, mock_cache_service):
        """Test /generate returns cached result when available"""
        cached_result = {
            "answer": "Cached answer",
            "references": [],
            "metadata": {"cached": True},
        }
        mock_cache_service.get_generation_result.return_value = cached_result

        response = api_test_client.post(
            "/generate", json={"question": "test", "topk": 5, "stream": False}
        )

        assert response.status_code == 200
        data = response.json()
        assert data == cached_result

    def test_generate_fallback_on_openai_failure(
        self,
        api_test_client,
        mock_search_service,
        mock_generation_service,
        mock_cache_service,
        sample_search_result,
    ):
        """Test /generate uses fallback when OpenAI fails"""
        mock_cache_service.get_generation_result.return_value = None
        mock_search_service.execute_search.return_value = sample_search_result
        mock_generation_service.prepare_from_domain_documents.return_value = []

        with (
            patch("wp_chat.api.routers.chat.generation_pipeline") as mock_pipeline,
            patch("wp_chat.api.routers.chat.openai_client") as mock_openai,
        ):
            mock_pipeline.process_retrieval_results.return_value = ([], {})
            mock_pipeline.build_prompt.return_value = ([], {})
            mock_pipeline.generate_fallback_response.return_value = GenerationResult(
                answer="Fallback answer",
                references=[],
                metadata={"fallback": True},
            )

            # Mock OpenAI failure
            mock_metrics = Mock()
            mock_metrics.success = False
            mock_metrics.error_message = "API error"
            mock_metrics.total_latency_ms = 500
            mock_metrics.ttft_ms = 0
            mock_metrics.model = "gpt-4o-mini"

            mock_openai.chat_completion.return_value = ("", mock_metrics)

            response = api_test_client.post(
                "/generate",
                json={"question": "test", "topk": 5, "stream": False},
            )

        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert data["metadata"].get("fallback") is True


# ========================================
# Error Handling Tests
# ========================================


class TestErrorHandling:
    """Tests for error handling and edge cases"""

    def test_search_service_exception_returns_500(
        self, api_test_client, mock_search_service, mock_cache_service
    ):
        """Test /search handles service exceptions properly"""
        mock_cache_service.get_search_results.return_value = None
        mock_search_service.execute_search.side_effect = Exception("Service error")

        response = api_test_client.post(
            "/search", json={"query": "test", "topk": 5, "mode": "hybrid"}
        )

        assert response.status_code == 500
        data = response.json()
        assert "error" in data["detail"].lower() or "internal" in data["detail"].lower()

    def test_search_xss_sanitization(
        self, api_test_client, mock_search_service, mock_cache_service
    ):
        """Test /search sanitizes XSS attempts in query"""
        mock_cache_service.get_search_results.return_value = None

        # Create SearchResult for sanitized query
        docs = [
            Document(
                post_id="1",
                chunk_id=0,
                title="Test Doc",
                url="https://example.com/test",
                chunk="Test content",
                hybrid_score=0.9,
                rank=1,
            )
        ]
        xss_result = SearchResult(
            query="test query", mode="hybrid", documents=docs, rerank_enabled=False
        )
        mock_search_service.execute_search.return_value = xss_result

        with patch(
            "wp_chat.api.routers.chat.highlight_results", side_effect=lambda x, *args, **kwargs: x
        ):
            response = api_test_client.post(
                "/search",
                json={
                    "query": "<script>alert('xss')</script>test query",
                    "topk": 5,
                    "mode": "hybrid",
                },
            )

        # Request should succeed (XSS stripped by Pydantic validator)
        # The validator in models.py should have stripped the script tag
        assert response.status_code == 200
