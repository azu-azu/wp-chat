"""
Unit tests for SearchResult domain model
"""

import pytest

from wp_chat.domain.models import Document, SearchResult


class TestSearchResult:
    """Test suite for SearchResult domain model"""

    def test_create_search_result_minimal(self):
        """Test creating a minimal search result"""
        docs = [
            Document(
                post_id="1",
                chunk_id=0,
                title="Test",
                url="https://example.com",
                chunk="content",
                hybrid_score=0.8,
            )
        ]
        result = SearchResult(
            query="test query",
            mode="hybrid",
            documents=docs,
        )
        assert result.query == "test query"
        assert result.mode == "hybrid"
        assert len(result.documents) == 1
        assert result.rerank_enabled is False
        assert result.total_candidates == 1

    def test_create_search_result_with_rerank(self):
        """Test creating search result with rerank enabled"""
        docs = [
            Document(
                post_id="1",
                chunk_id=0,
                title="Test",
                url="https://example.com",
                chunk="content",
                hybrid_score=0.8,
                ce_score=0.9,
            )
        ]
        result = SearchResult(
            query="test query",
            mode="hybrid",
            documents=docs,
            rerank_enabled=True,
        )
        assert result.rerank_enabled is True

    def test_post_init_sets_total_candidates(self):
        """Test __post_init__ sets total_candidates from documents length"""
        docs = [
            Document(
                post_id="1",
                chunk_id=0,
                title="Test 1",
                url="https://example.com/1",
                chunk="content 1",
                hybrid_score=0.8,
            ),
            Document(
                post_id="2",
                chunk_id=0,
                title="Test 2",
                url="https://example.com/2",
                chunk="content 2",
                hybrid_score=0.7,
            ),
        ]
        result = SearchResult(query="test", mode="hybrid", documents=docs)
        assert result.total_candidates == 2

    def test_post_init_respects_explicit_total_candidates(self):
        """Test __post_init__ does not override explicit total_candidates"""
        docs = [
            Document(
                post_id="1",
                chunk_id=0,
                title="Test",
                url="https://example.com",
                chunk="content",
                hybrid_score=0.8,
            )
        ]
        result = SearchResult(
            query="test",
            mode="hybrid",
            documents=docs,
            total_candidates=100,
        )
        assert result.total_candidates == 100

    def test_get_top_k_less_than_available(self):
        """Test get_top_k with k less than available documents"""
        docs = [
            Document(
                post_id=str(i),
                chunk_id=0,
                title=f"Test {i}",
                url=f"https://example.com/{i}",
                chunk=f"content {i}",
                hybrid_score=0.9 - i * 0.1,
            )
            for i in range(5)
        ]
        result = SearchResult(query="test", mode="hybrid", documents=docs)
        top3 = result.get_top_k(3)
        assert len(top3) == 3
        assert top3[0].post_id == "0"
        assert top3[1].post_id == "1"
        assert top3[2].post_id == "2"

    def test_get_top_k_more_than_available(self):
        """Test get_top_k with k more than available documents"""
        docs = [
            Document(
                post_id="1",
                chunk_id=0,
                title="Test",
                url="https://example.com",
                chunk="content",
                hybrid_score=0.8,
            )
        ]
        result = SearchResult(query="test", mode="hybrid", documents=docs)
        top5 = result.get_top_k(5)
        assert len(top5) == 1

    def test_filter_by_relevance_default_threshold(self):
        """Test filtering by relevance with default threshold (0.7)"""
        docs = [
            Document(
                post_id="1",
                chunk_id=0,
                title="High score",
                url="https://example.com/1",
                chunk="content",
                hybrid_score=0.85,
            ),
            Document(
                post_id="2",
                chunk_id=0,
                title="Medium score",
                url="https://example.com/2",
                chunk="content",
                hybrid_score=0.65,
            ),
            Document(
                post_id="3",
                chunk_id=0,
                title="Exact threshold",
                url="https://example.com/3",
                chunk="content",
                hybrid_score=0.7,
            ),
        ]
        result = SearchResult(query="test", mode="hybrid", documents=docs)
        filtered = result.filter_by_relevance()
        assert len(filtered) == 2
        assert filtered[0].post_id == "1"
        assert filtered[1].post_id == "3"

    def test_filter_by_relevance_custom_threshold(self):
        """Test filtering by relevance with custom threshold"""
        docs = [
            Document(
                post_id="1",
                chunk_id=0,
                title="High",
                url="https://example.com/1",
                chunk="content",
                hybrid_score=0.85,
            ),
            Document(
                post_id="2",
                chunk_id=0,
                title="Low",
                url="https://example.com/2",
                chunk="content",
                hybrid_score=0.65,
            ),
        ]
        result = SearchResult(query="test", mode="hybrid", documents=docs)
        filtered = result.filter_by_relevance(threshold=0.8)
        assert len(filtered) == 1
        assert filtered[0].post_id == "1"

    def test_get_highly_relevant_default_threshold(self):
        """Test getting highly relevant documents (default threshold 0.85)"""
        docs = [
            Document(
                post_id="1",
                chunk_id=0,
                title="Very high",
                url="https://example.com/1",
                chunk="content",
                hybrid_score=0.9,
            ),
            Document(
                post_id="2",
                chunk_id=0,
                title="Medium",
                url="https://example.com/2",
                chunk="content",
                hybrid_score=0.8,
            ),
            Document(
                post_id="3",
                chunk_id=0,
                title="Exact threshold",
                url="https://example.com/3",
                chunk="content",
                hybrid_score=0.85,
            ),
        ]
        result = SearchResult(query="test", mode="hybrid", documents=docs)
        highly_relevant = result.get_highly_relevant()
        assert len(highly_relevant) == 2
        assert highly_relevant[0].post_id == "1"
        assert highly_relevant[1].post_id == "3"

    def test_get_highly_relevant_custom_threshold(self):
        """Test getting highly relevant documents with custom threshold"""
        docs = [
            Document(
                post_id="1",
                chunk_id=0,
                title="Very high",
                url="https://example.com/1",
                chunk="content",
                hybrid_score=0.95,
            ),
            Document(
                post_id="2",
                chunk_id=0,
                title="High",
                url="https://example.com/2",
                chunk="content",
                hybrid_score=0.88,
            ),
        ]
        result = SearchResult(query="test", mode="hybrid", documents=docs)
        highly_relevant = result.get_highly_relevant(threshold=0.9)
        assert len(highly_relevant) == 1
        assert highly_relevant[0].post_id == "1"

    def test_has_results_with_documents(self):
        """Test has_results returns True when documents exist"""
        docs = [
            Document(
                post_id="1",
                chunk_id=0,
                title="Test",
                url="https://example.com",
                chunk="content",
                hybrid_score=0.8,
            )
        ]
        result = SearchResult(query="test", mode="hybrid", documents=docs)
        assert result.has_results() is True

    def test_has_results_empty(self):
        """Test has_results returns False when no documents"""
        result = SearchResult(query="test", mode="hybrid", documents=[])
        assert result.has_results() is False

    def test_count(self):
        """Test count returns correct number of documents"""
        docs = [
            Document(
                post_id=str(i),
                chunk_id=0,
                title=f"Test {i}",
                url=f"https://example.com/{i}",
                chunk=f"content {i}",
                hybrid_score=0.8,
            )
            for i in range(3)
        ]
        result = SearchResult(query="test", mode="hybrid", documents=docs)
        assert result.count() == 3

    def test_get_average_score_multiple_documents(self):
        """Test average score calculation with multiple documents"""
        docs = [
            Document(
                post_id="1",
                chunk_id=0,
                title="Test 1",
                url="https://example.com/1",
                chunk="content",
                hybrid_score=0.8,
            ),
            Document(
                post_id="2",
                chunk_id=0,
                title="Test 2",
                url="https://example.com/2",
                chunk="content",
                hybrid_score=0.6,
            ),
        ]
        result = SearchResult(query="test", mode="hybrid", documents=docs)
        avg = result.get_average_score()
        assert avg == pytest.approx(0.7)

    def test_get_average_score_with_ce_scores(self):
        """Test average score uses effective scores (ce_score if available)"""
        docs = [
            Document(
                post_id="1",
                chunk_id=0,
                title="Test 1",
                url="https://example.com/1",
                chunk="content",
                hybrid_score=0.7,
                ce_score=0.9,
            ),
            Document(
                post_id="2",
                chunk_id=0,
                title="Test 2",
                url="https://example.com/2",
                chunk="content",
                hybrid_score=0.8,
            ),
        ]
        result = SearchResult(query="test", mode="hybrid", documents=docs)
        avg = result.get_average_score()
        # (0.9 + 0.8) / 2 = 0.85
        assert avg == pytest.approx(0.85)

    def test_get_average_score_empty_documents(self):
        """Test average score returns 0.0 for empty documents"""
        result = SearchResult(query="test", mode="hybrid", documents=[])
        assert result.get_average_score() == 0.0

    def test_get_unique_sources(self):
        """Test getting unique source URLs"""
        docs = [
            Document(
                post_id="1",
                chunk_id=0,
                title="Test 1",
                url="https://example.com/page1",
                chunk="content 1",
                hybrid_score=0.8,
            ),
            Document(
                post_id="2",
                chunk_id=1,
                title="Test 2",
                url="https://example.com/page1",  # Same URL
                chunk="content 2",
                hybrid_score=0.7,
            ),
            Document(
                post_id="3",
                chunk_id=0,
                title="Test 3",
                url="https://example.com/page2",
                chunk="content 3",
                hybrid_score=0.9,
            ),
        ]
        result = SearchResult(query="test", mode="hybrid", documents=docs)
        unique_sources = result.get_unique_sources()
        assert len(unique_sources) == 2
        assert "https://example.com/page1" in unique_sources
        assert "https://example.com/page2" in unique_sources

    def test_to_dict_minimal(self):
        """Test converting search result to dict (minimal)"""
        docs = [
            Document(
                post_id="1",
                chunk_id=0,
                title="Test",
                url="https://example.com",
                chunk="content",
                hybrid_score=0.8,
            )
        ]
        result = SearchResult(query="test query", mode="hybrid", documents=docs)
        result_dict = result.to_dict()

        assert result_dict["query"] == "test query"
        assert result_dict["mode"] == "hybrid"
        assert result_dict["rerank_enabled"] is False
        assert result_dict["total_candidates"] == 1
        assert result_dict["result_count"] == 1
        assert len(result_dict["documents"]) == 1
        assert result_dict["metadata"] == {}

    def test_to_dict_with_metadata(self):
        """Test converting search result to dict with metadata"""
        docs = [
            Document(
                post_id="1",
                chunk_id=0,
                title="Test",
                url="https://example.com",
                chunk="content",
                hybrid_score=0.8,
            )
        ]
        metadata = {"search_time_ms": 150, "index_version": "v1"}
        result = SearchResult(
            query="test",
            mode="hybrid",
            documents=docs,
            metadata=metadata,
        )
        result_dict = result.to_dict()
        assert result_dict["metadata"]["search_time_ms"] == 150
        assert result_dict["metadata"]["index_version"] == "v1"

    def test_to_dict_with_rerank_enabled(self):
        """Test converting search result to dict with rerank enabled"""
        docs = [
            Document(
                post_id="1",
                chunk_id=0,
                title="Test",
                url="https://example.com",
                chunk="content",
                hybrid_score=0.8,
                ce_score=0.9,
            )
        ]
        result = SearchResult(
            query="test",
            mode="hybrid",
            documents=docs,
            rerank_enabled=True,
        )
        result_dict = result.to_dict()
        assert result_dict["rerank_enabled"] is True
        assert result_dict["documents"][0]["ce_score"] == 0.9

    def test_from_tuples_basic(self):
        """Test creating SearchResult from tuples"""
        meta = [
            {
                "post_id": "1",
                "chunk_id": 0,
                "title": "Test 1",
                "url": "https://example.com/1",
                "chunk": "content 1",
            },
            {
                "post_id": "2",
                "chunk_id": 0,
                "title": "Test 2",
                "url": "https://example.com/2",
                "chunk": "content 2",
            },
        ]
        results = [
            (0, 0.85, None),
            (1, 0.75, None),
        ]

        search_result = SearchResult.from_tuples(
            query="test query",
            mode="hybrid",
            results=results,
            meta=meta,
        )

        assert search_result.query == "test query"
        assert search_result.mode == "hybrid"
        assert len(search_result.documents) == 2
        assert search_result.documents[0].post_id == "1"
        assert search_result.documents[0].hybrid_score == 0.85
        assert search_result.documents[0].rank == 1
        assert search_result.documents[1].rank == 2

    def test_from_tuples_with_ce_scores(self):
        """Test creating SearchResult from tuples with CE scores"""
        meta = [
            {
                "post_id": "1",
                "chunk_id": 0,
                "title": "Test",
                "url": "https://example.com",
                "chunk": "content",
            }
        ]
        results = [(0, 0.75, 0.9)]

        search_result = SearchResult.from_tuples(
            query="test",
            mode="hybrid",
            results=results,
            meta=meta,
            rerank_enabled=True,
        )

        assert search_result.rerank_enabled is True
        assert search_result.documents[0].ce_score == 0.9

    def test_from_tuples_with_invalid_indices(self):
        """Test from_tuples skips invalid indices"""
        meta = [
            {
                "post_id": "1",
                "chunk_id": 0,
                "title": "Test",
                "url": "https://example.com",
                "chunk": "content",
            }
        ]
        # Index 5 is out of range
        results = [
            (0, 0.85, None),
            (5, 0.75, None),  # Invalid index
        ]

        search_result = SearchResult.from_tuples(
            query="test",
            mode="hybrid",
            results=results,
            meta=meta,
        )

        # Only the valid document should be included
        assert len(search_result.documents) == 1
        assert search_result.documents[0].post_id == "1"
        # total_candidates includes invalid results too
        assert search_result.total_candidates == 2


class TestSearchResultEdgeCases:
    """Test edge cases for SearchResult model"""

    def test_empty_search_result(self):
        """Test search result with no documents"""
        result = SearchResult(query="test", mode="hybrid", documents=[])
        assert result.has_results() is False
        assert result.count() == 0
        assert result.get_average_score() == 0.0
        assert len(result.get_unique_sources()) == 0
        assert result.filter_by_relevance() == []
        assert result.get_highly_relevant() == []

    def test_single_document_result(self):
        """Test search result with single document"""
        doc = Document(
            post_id="1",
            chunk_id=0,
            title="Test",
            url="https://example.com",
            chunk="content",
            hybrid_score=0.8,
        )
        result = SearchResult(query="test", mode="hybrid", documents=[doc])
        assert result.has_results() is True
        assert result.count() == 1
        assert result.get_average_score() == 0.8
        assert result.get_top_k(10) == [doc]

    def test_all_documents_below_threshold(self):
        """Test filtering when all documents are below threshold"""
        docs = [
            Document(
                post_id=str(i),
                chunk_id=0,
                title=f"Test {i}",
                url=f"https://example.com/{i}",
                chunk=f"content {i}",
                hybrid_score=0.5,
            )
            for i in range(3)
        ]
        result = SearchResult(query="test", mode="hybrid", documents=docs)
        filtered = result.filter_by_relevance(threshold=0.8)
        assert len(filtered) == 0

    def test_all_documents_above_threshold(self):
        """Test filtering when all documents are above threshold"""
        docs = [
            Document(
                post_id=str(i),
                chunk_id=0,
                title=f"Test {i}",
                url=f"https://example.com/{i}",
                chunk=f"content {i}",
                hybrid_score=0.9,
            )
            for i in range(3)
        ]
        result = SearchResult(query="test", mode="hybrid", documents=docs)
        filtered = result.filter_by_relevance(threshold=0.7)
        assert len(filtered) == 3

    def test_different_search_modes(self):
        """Test search result with different modes"""
        doc = Document(
            post_id="1",
            chunk_id=0,
            title="Test",
            url="https://example.com",
            chunk="content",
            hybrid_score=0.8,
        )

        for mode in ["dense", "bm25", "hybrid"]:
            result = SearchResult(query="test", mode=mode, documents=[doc])
            assert result.mode == mode
            result_dict = result.to_dict()
            assert result_dict["mode"] == mode

    def test_unicode_in_query(self):
        """Test search result with unicode query"""
        doc = Document(
            post_id="1",
            chunk_id=0,
            title="日本語タイトル",
            url="https://example.com",
            chunk="日本語コンテンツ",
            hybrid_score=0.8,
        )
        result = SearchResult(query="日本語検索", mode="hybrid", documents=[doc])
        assert result.query == "日本語検索"
        result_dict = result.to_dict()
        assert result_dict["query"] == "日本語検索"

    def test_from_tuples_empty_results(self):
        """Test creating SearchResult from empty tuples"""
        meta = [
            {
                "post_id": "1",
                "chunk_id": 0,
                "title": "Test",
                "url": "https://example.com",
                "chunk": "content",
            }
        ]
        results = []

        search_result = SearchResult.from_tuples(
            query="test",
            mode="hybrid",
            results=results,
            meta=meta,
        )

        assert search_result.has_results() is False
        assert search_result.count() == 0
        assert search_result.total_candidates == 0
