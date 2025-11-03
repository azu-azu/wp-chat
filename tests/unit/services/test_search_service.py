"""
Unit tests for SearchService
"""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from wp_chat.services.search_service import SearchService


@pytest.fixture
def mock_model():
    """Mock SentenceTransformer model"""
    model = MagicMock()
    model.encode.return_value = np.array([0.1, 0.2, 0.3], dtype="float32")
    return model


@pytest.fixture
def mock_index():
    """Mock FAISS index"""
    index = MagicMock()
    # Default search result: distances and indices
    index.search.return_value = (
        np.array([[0.9, 0.8, 0.7]], dtype="float32"),  # Distances
        np.array([[0, 1, 2]], dtype="int64"),  # Indices
    )
    return index


@pytest.fixture
def sample_meta():
    """Sample metadata for testing"""
    return [
        {
            "post_id": "1",
            "chunk_id": 0,
            "title": "WordPress Security",
            "url": "https://example.com/security",
            "chunk": "Security is important.",
        },
        {
            "post_id": "2",
            "chunk_id": 0,
            "title": "SEO Tips",
            "url": "https://example.com/seo",
            "chunk": "SEO optimization.",
        },
        {
            "post_id": "3",
            "chunk_id": 0,
            "title": "Performance",
            "url": "https://example.com/performance",
            "chunk": "Performance matters.",
        },
    ]


@pytest.fixture
def mock_tfidf_vec():
    """Mock TF-IDF vectorizer"""
    vec = MagicMock()
    # Return a sparse matrix mock
    sparse_mock = MagicMock()
    vec.transform.return_value = sparse_mock
    return vec


@pytest.fixture
def mock_tfidf_mat():
    """Mock TF-IDF matrix"""
    # Create a simple sparse matrix mock
    mat = MagicMock()
    # Mock matrix multiplication result
    result_mock = MagicMock()
    result_mock.toarray.return_value = np.array([[0.8], [0.6], [0.4]])
    mat.__matmul__ = MagicMock(return_value=result_mock)
    return mat


@pytest.fixture
def search_service(mock_model, mock_index, sample_meta, mock_tfidf_vec, mock_tfidf_mat):
    """SearchService instance with mocked dependencies"""
    return SearchService(
        model=mock_model,
        index=mock_index,
        meta=sample_meta,
        tfidf_vec=mock_tfidf_vec,
        tfidf_mat=mock_tfidf_mat,
    )


class TestSearchService:
    """Test suite for SearchService"""

    def test_init(self, mock_model, mock_index, sample_meta, mock_tfidf_vec, mock_tfidf_mat):
        """Test service initialization"""
        service = SearchService(
            model=mock_model,
            index=mock_index,
            meta=sample_meta,
            tfidf_vec=mock_tfidf_vec,
            tfidf_mat=mock_tfidf_mat,
        )

        assert service.model == mock_model
        assert service.index == mock_index
        assert service.meta == sample_meta
        assert service.tfidf_vec == mock_tfidf_vec
        assert service.tfidf_mat == mock_tfidf_mat

    def test_minmax_basic(self, search_service):
        """Test min-max normalization"""
        x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        normalized = search_service._minmax(x)

        assert normalized.min() == pytest.approx(0.0)
        assert normalized.max() == pytest.approx(1.0)
        assert len(normalized) == 5

    def test_minmax_all_same_values(self, search_service):
        """Test min-max normalization when all values are the same"""
        x = np.array([5.0, 5.0, 5.0])
        normalized = search_service._minmax(x)

        # Should handle division by zero with epsilon
        assert len(normalized) == 3
        assert np.all(np.isfinite(normalized))

    def test_minmax_negative_values(self, search_service):
        """Test min-max normalization with negative values"""
        x = np.array([-2.0, -1.0, 0.0, 1.0, 2.0])
        normalized = search_service._minmax(x)

        assert normalized.min() == pytest.approx(0.0)
        assert normalized.max() == pytest.approx(1.0)

    def test_search_dense_basic(self, search_service, mock_model, mock_index):
        """Test dense search"""
        query = "test query"
        topk = 3

        results = search_service.search_dense(query, topk)

        # Check model.encode was called
        mock_model.encode.assert_called_once()
        assert mock_model.encode.call_args[0][0] == query

        # Check index.search was called
        mock_index.search.assert_called_once()

        # Check results format
        assert len(results) == 3
        assert results[0] == (0, pytest.approx(0.9, abs=0.001))
        assert results[1] == (1, pytest.approx(0.8, abs=0.001))
        assert results[2] == (2, pytest.approx(0.7, abs=0.001))

    def test_search_dense_custom_topk(self, search_service, mock_index):
        """Test dense search with different topk"""
        mock_index.search.return_value = (
            np.array([[0.95, 0.85]], dtype="float32"),
            np.array([[5, 10]], dtype="int64"),
        )

        results = search_service.search_dense("query", topk=2)

        assert len(results) == 2
        assert results[0] == (5, pytest.approx(0.95, abs=0.001))
        assert results[1] == (10, pytest.approx(0.85, abs=0.001))

    def test_search_bm25_basic(self, search_service, mock_tfidf_vec, mock_tfidf_mat):
        """Test BM25 search"""
        query = "test query"
        topk = 3

        # Mock the sparse matrix multiplication result
        result_mock = MagicMock()
        result_mock.toarray.return_value = np.array([[0.8], [0.6], [0.4]])
        mock_tfidf_mat.__matmul__ = MagicMock(return_value=result_mock)

        results = search_service.search_bm25(query, topk)

        # Check vectorizer was called
        mock_tfidf_vec.transform.assert_called_once_with([query])

        # Check results (should be sorted by score descending)
        assert len(results) == 3
        assert results[0] == (0, 0.8)
        assert results[1] == (1, 0.6)
        assert results[2] == (2, 0.4)

    def test_search_bm25_without_index(self, mock_model, mock_index, sample_meta):
        """Test BM25 search when index is not built"""
        service = SearchService(
            model=mock_model,
            index=mock_index,
            meta=sample_meta,
            tfidf_vec=None,  # Not built
            tfidf_mat=None,
        )

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            service.search_bm25("query", 5)

        assert exc_info.value.status_code == 400
        assert "BM25 index not built" in str(exc_info.value.detail)

    def test_execute_search_dense_mode(self, search_service, mock_model, mock_index):
        """Test execute_search with dense mode"""
        mock_index.search.return_value = (
            np.array([[0.9, 0.8]], dtype="float32"),
            np.array([[0, 1]], dtype="int64"),
        )

        result = search_service.execute_search(
            query="test query", topk=2, mode="dense", rerank=False
        )

        assert result.query == "test query"
        assert result.mode == "dense"
        assert result.rerank_enabled is False
        assert len(result.documents) == 2
        assert result.documents[0].hybrid_score == pytest.approx(0.9, abs=0.001)

    def test_execute_search_bm25_mode(self, search_service):
        """Test execute_search with bm25 mode"""
        result = search_service.execute_search(
            query="test query", topk=2, mode="bm25", rerank=False
        )

        assert result.query == "test query"
        assert result.mode == "bm25"
        assert result.rerank_enabled is False
        assert len(result.documents) <= 2

    def test_execute_search_invalid_mode(self, search_service):
        """Test execute_search with invalid mode"""
        with pytest.raises(ValueError) as exc_info:
            search_service.execute_search(query="test", topk=5, mode="invalid")

        assert "Invalid search mode" in str(exc_info.value)

    def test_execute_search_validates_query(self, search_service):
        """Test execute_search validates query using Query value object"""
        from fastapi import HTTPException

        # Empty query should raise error
        with pytest.raises(HTTPException) as exc_info:
            search_service.execute_search(query="", topk=5, mode="dense")

        assert exc_info.value.status_code == 400
        assert "empty" in str(exc_info.value.detail).lower()

    def test_execute_search_whitespace_query(self, search_service):
        """Test execute_search with whitespace-only query"""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            search_service.execute_search(query="   ", topk=5, mode="dense")

        assert exc_info.value.status_code == 400

    def test_execute_search_normalizes_query(self, search_service, mock_model):
        """Test execute_search normalizes query whitespace"""
        search_service.execute_search(query="  test   query  ", topk=2, mode="dense", rerank=False)

        # Should normalize to "test query"
        call_args = mock_model.encode.call_args_list
        # The query should be normalized when passed to model
        assert any("test query" in str(call) for call in call_args)


class TestSearchServiceHybridSearch:
    """Test hybrid search functionality"""

    @patch("wp_chat.services.search_service.dedup_by_article")
    @patch("wp_chat.services.search_service.mmr_diversify")
    def test_search_hybrid_basic(
        self, mock_mmr, mock_dedup, search_service, mock_model, mock_tfidf_mat
    ):
        """Test basic hybrid search without reranking"""
        # Setup mocks
        mock_dedup.return_value = []  # Return empty for simplicity
        mock_mmr.return_value = []

        results, rerank_status = search_service.search_hybrid_with_rerank(
            query="test", topk=5, rerank=False
        )

        assert isinstance(results, list)
        assert rerank_status is False
        mock_dedup.assert_called_once()
        mock_mmr.assert_called_once()

    @patch("wp_chat.services.search_service.CrossEncoderReranker")
    @patch("wp_chat.services.search_service.rerank_with_ce")
    @patch("wp_chat.services.search_service.dedup_by_article")
    @patch("wp_chat.services.search_service.mmr_diversify")
    def test_search_hybrid_with_rerank(
        self,
        mock_mmr,
        mock_dedup,
        mock_rerank_ce,
        mock_ce_class,
        search_service,
    ):
        """Test hybrid search with reranking enabled"""
        # Setup mocks
        mock_dedup.return_value = []
        mock_mmr.return_value = []
        mock_rerank_ce.return_value = []

        results, rerank_status = search_service.search_hybrid_with_rerank(
            query="test", topk=5, rerank=True
        )

        assert rerank_status is True
        mock_ce_class.assert_called_once()
        mock_rerank_ce.assert_called_once()

    @patch("wp_chat.services.search_service.CrossEncoderReranker")
    @patch("wp_chat.services.search_service.dedup_by_article")
    @patch("wp_chat.services.search_service.mmr_diversify")
    def test_search_hybrid_rerank_fallback(
        self,
        mock_mmr,
        mock_dedup,
        mock_ce_class,
        search_service,
    ):
        """Test hybrid search falls back when reranking fails"""
        # Setup mocks
        mock_dedup.return_value = []
        mock_mmr.return_value = []
        mock_ce_class.side_effect = Exception("Reranking failed")

        results, rerank_status = search_service.search_hybrid_with_rerank(
            query="test", topk=5, rerank=True
        )

        # Should fallback to hybrid scores
        assert rerank_status is False

    def test_execute_search_hybrid_mode(self, search_service):
        """Test execute_search with hybrid mode"""
        with patch.object(search_service, "search_hybrid_with_rerank") as mock_hybrid:
            mock_hybrid.return_value = ([], False)

            result = search_service.execute_search(
                query="test query", topk=5, mode="hybrid", rerank=False
            )

            assert result.mode == "hybrid"
            mock_hybrid.assert_called_once()


class TestSearchServiceEdgeCases:
    """Test edge cases for SearchService"""

    def test_search_dense_empty_results(self, search_service, mock_index):
        """Test dense search with no results"""
        mock_index.search.return_value = (
            np.array([[]], dtype="float32").reshape(1, 0),
            np.array([[]], dtype="int64").reshape(1, 0),
        )

        results = search_service.search_dense("query", topk=10)
        assert results == []

    def test_search_bm25_zero_scores(self, search_service, mock_tfidf_mat):
        """Test BM25 search when all scores are zero"""
        result_mock = MagicMock()
        result_mock.toarray.return_value = np.array([[0.0], [0.0], [0.0]])
        mock_tfidf_mat.__matmul__ = MagicMock(return_value=result_mock)

        results = search_service.search_bm25("query", topk=3)

        assert len(results) == 3
        assert all(score == 0.0 for _, score in results)

    def test_minmax_single_value(self, search_service):
        """Test min-max normalization with single value"""
        x = np.array([5.0])
        normalized = search_service._minmax(x)

        assert len(normalized) == 1
        assert np.isfinite(normalized[0])

    def test_minmax_zero_values(self, search_service):
        """Test min-max normalization with all zeros"""
        x = np.array([0.0, 0.0, 0.0])
        normalized = search_service._minmax(x)

        assert len(normalized) == 3
        assert np.all(np.isfinite(normalized))

    def test_execute_search_very_long_query(self, search_service):
        """Test execute_search with very long query"""
        from fastapi import HTTPException

        long_query = "a" * 1001  # Exceeds Query max length

        with pytest.raises(HTTPException) as exc_info:
            search_service.execute_search(query=long_query, topk=5, mode="dense")

        assert exc_info.value.status_code == 400
        assert "exceeds maximum length" in str(exc_info.value.detail).lower()

    def test_execute_search_topk_zero(self, search_service, mock_index):
        """Test execute_search with topk=0"""
        mock_index.search.return_value = (
            np.array([[]], dtype="float32").reshape(1, 0),
            np.array([[]], dtype="int64").reshape(1, 0),
        )

        result = search_service.execute_search(query="test", topk=0, mode="dense", rerank=False)

        assert len(result.documents) == 0

    def test_execute_search_topk_large(self, search_service, mock_index):
        """Test execute_search with very large topk"""
        # Return 3 results even though topk is 1000
        mock_index.search.return_value = (
            np.array([[0.9, 0.8, 0.7]], dtype="float32"),
            np.array([[0, 1, 2]], dtype="int64"),
        )

        result = search_service.execute_search(query="test", topk=1000, mode="dense", rerank=False)

        # Should return available results (3)
        assert len(result.documents) == 3

    def test_search_dense_unicode_query(self, search_service, mock_model):
        """Test dense search with unicode query"""
        query = "日本語のクエリ"
        search_service.search_dense(query, topk=5)

        mock_model.encode.assert_called_once()
        assert mock_model.encode.call_args[0][0] == query

    def test_search_bm25_unicode_query(self, search_service, mock_tfidf_vec):
        """Test BM25 search with unicode query"""
        query = "日本語のクエリ"
        search_service.search_bm25(query, topk=5)

        mock_tfidf_vec.transform.assert_called_once_with([query])

    def test_execute_search_result_has_correct_structure(self, search_service, mock_index):
        """Test that execute_search returns properly structured SearchResult"""
        mock_index.search.return_value = (
            np.array([[0.9]], dtype="float32"),
            np.array([[0]], dtype="int64"),
        )

        result = search_service.execute_search(query="test", topk=1, mode="dense", rerank=False)

        # Check SearchResult structure
        assert hasattr(result, "query")
        assert hasattr(result, "mode")
        assert hasattr(result, "documents")
        assert hasattr(result, "rerank_enabled")

        # Check Document structure
        assert len(result.documents) == 1
        doc = result.documents[0]
        assert hasattr(doc, "post_id")
        assert hasattr(doc, "title")
        assert hasattr(doc, "url")
        assert hasattr(doc, "chunk")
        assert hasattr(doc, "hybrid_score")

    def test_service_with_none_tfidf(self, mock_model, mock_index, sample_meta):
        """Test service initialization with None TF-IDF components"""
        service = SearchService(
            model=mock_model,
            index=mock_index,
            meta=sample_meta,
            tfidf_vec=None,
            tfidf_mat=None,
        )

        assert service.tfidf_vec is None
        assert service.tfidf_mat is None

        # BM25 search should fail
        from fastapi import HTTPException

        with pytest.raises(HTTPException):
            service.search_bm25("query", 5)

    def test_empty_meta(self, mock_model, mock_index, mock_tfidf_vec, mock_tfidf_mat):
        """Test service with empty metadata"""
        service = SearchService(
            model=mock_model,
            index=mock_index,
            meta=[],
            tfidf_vec=mock_tfidf_vec,
            tfidf_mat=mock_tfidf_mat,
        )

        mock_index.search.return_value = (
            np.array([[0.9]], dtype="float32"),
            np.array([[0]], dtype="int64"),
        )

        result = service.execute_search(query="test", topk=5, mode="dense")

        # Should handle gracefully
        assert len(result.documents) == 0
