"""
Unit tests for GenerationService
"""

import pytest

from wp_chat.domain.models import Document
from wp_chat.services.generation_service import GenerationService


@pytest.fixture
def sample_meta():
    """Sample metadata for testing"""
    return [
        {
            "post_id": "1",
            "chunk_id": 0,
            "title": "WordPress Security",
            "url": "https://example.com/security",
            "chunk": "WordPress security is important for protecting your website.",
        },
        {
            "post_id": "2",
            "chunk_id": 0,
            "title": "SEO Best Practices",
            "url": "https://example.com/seo",
            "chunk": "SEO optimization helps your site rank better in search engines.",
        },
        {
            "post_id": "3",
            "chunk_id": 1,
            "title": "Performance Tips",
            "url": "https://example.com/performance",
            "chunk": "a" * 500,  # Long content for snippet testing
        },
    ]


@pytest.fixture
def generation_service(sample_meta):
    """GenerationService instance with sample metadata"""
    return GenerationService(meta=sample_meta)


class TestGenerationService:
    """Test suite for GenerationService"""

    def test_init(self, sample_meta):
        """Test service initialization"""
        service = GenerationService(meta=sample_meta)
        assert service.meta == sample_meta
        assert len(service.meta) == 3

    def test_create_snippet_short_text(self, generation_service):
        """Test snippet creation with short text"""
        text = "Short text"
        snippet = generation_service._create_snippet(text)
        assert snippet == "Short text"

    def test_create_snippet_long_text_default_length(self, generation_service):
        """Test snippet creation with long text (default max_length=400)"""
        text = "a" * 500
        snippet = generation_service._create_snippet(text)
        assert len(snippet) == 401  # 400 + "…"
        assert snippet.endswith("…")
        assert snippet[:-1] == "a" * 400

    def test_create_snippet_custom_length(self, generation_service):
        """Test snippet creation with custom max_length"""
        text = "a" * 200
        snippet = generation_service._create_snippet(text, max_length=100)
        assert len(snippet) == 101  # 100 + "…"
        assert snippet.endswith("…")

    def test_create_snippet_exact_length(self, generation_service):
        """Test snippet when text is exactly max_length"""
        text = "a" * 400
        snippet = generation_service._create_snippet(text, max_length=400)
        assert snippet == text
        assert not snippet.endswith("…")

    def test_convert_hits_to_documents_basic(self, generation_service):
        """Test converting basic hits (idx, score) format"""
        hits = [
            (0, 0.85),
            (1, 0.75),
        ]
        question = "test question"

        docs, rerank_status = generation_service.convert_hits_to_documents(hits, question)

        assert len(docs) == 2
        assert rerank_status is False

        # Check first document
        assert docs[0]["rank"] == 1
        assert docs[0]["hybrid_score"] == 0.85
        assert docs[0]["post_id"] == "1"
        assert docs[0]["chunk_id"] == 0
        assert docs[0]["title"] == "WordPress Security"
        assert docs[0]["url"] == "https://example.com/security"
        assert "ce_score" not in docs[0]

    def test_convert_hits_to_documents_with_ce_score(self, generation_service):
        """Test converting hits with cross-encoder scores"""
        hits = [
            (0, 0.75, 0.9),
            (1, 0.65, 0.85),
        ]
        question = "test question"

        docs, rerank_status = generation_service.convert_hits_to_documents(hits, question)

        assert len(docs) == 2
        assert rerank_status is True

        # Check ce_score is included
        assert docs[0]["ce_score"] == 0.9
        assert docs[1]["ce_score"] == 0.85

    def test_convert_hits_to_documents_with_none_ce_score(self, generation_service):
        """Test converting hits with None ce_score (3-tuple format but no rerank)"""
        hits = [
            (0, 0.85, None),
            (1, 0.75, None),
        ]
        question = "test question"

        docs, rerank_status = generation_service.convert_hits_to_documents(hits, question)

        assert len(docs) == 2
        assert rerank_status is False
        assert "ce_score" not in docs[0]
        assert "ce_score" not in docs[1]

    def test_convert_hits_to_documents_mixed_ce_scores(self, generation_service):
        """Test converting hits with mixed ce_scores (some None, some not)"""
        hits = [
            (0, 0.85, 0.9),  # Has ce_score
            (1, 0.75, None),  # No ce_score
        ]
        question = "test question"

        docs, rerank_status = generation_service.convert_hits_to_documents(hits, question)

        assert len(docs) == 2
        assert rerank_status is True  # At least one has ce_score
        assert "ce_score" in docs[0]
        assert docs[0]["ce_score"] == 0.9
        assert "ce_score" not in docs[1]

    def test_convert_hits_to_documents_invalid_index_negative(self, generation_service):
        """Test converting hits with negative index (should skip)"""
        hits = [
            (0, 0.85),
            (-1, 0.75),  # Invalid index
            (1, 0.65),
        ]
        question = "test question"

        docs, rerank_status = generation_service.convert_hits_to_documents(hits, question)

        assert len(docs) == 2  # -1 index skipped
        assert docs[0]["post_id"] == "1"
        assert docs[1]["post_id"] == "2"

    def test_convert_hits_to_documents_invalid_index_out_of_range(self, generation_service):
        """Test converting hits with out-of-range index (should skip)"""
        hits = [
            (0, 0.85),
            (10, 0.75),  # Index out of range (meta only has 3 items)
            (1, 0.65),
        ]
        question = "test question"

        docs, rerank_status = generation_service.convert_hits_to_documents(hits, question)

        assert len(docs) == 2  # Index 10 skipped
        assert docs[0]["post_id"] == "1"
        assert docs[1]["post_id"] == "2"

    def test_convert_hits_to_documents_rank_assignment(self, generation_service):
        """Test that rank is assigned sequentially starting from 1"""
        hits = [
            (2, 0.9),
            (0, 0.8),
            (1, 0.7),
        ]
        question = "test question"

        docs, rerank_status = generation_service.convert_hits_to_documents(hits, question)

        assert docs[0]["rank"] == 1
        assert docs[1]["rank"] == 2
        assert docs[2]["rank"] == 3

    def test_convert_hits_to_documents_snippet_creation(self, generation_service):
        """Test that snippets are created for documents"""
        hits = [(2, 0.9)]  # Index 2 has long content (500 chars)
        question = "test question"

        docs, rerank_status = generation_service.convert_hits_to_documents(hits, question)

        assert len(docs[0]["snippet"]) == 401  # 400 + "…"
        assert docs[0]["snippet"].endswith("…")
        assert len(docs[0]["chunk"]) == 500  # Original chunk unchanged

    def test_convert_hits_to_documents_empty_hits(self, generation_service):
        """Test converting empty hits list"""
        hits = []
        question = "test question"

        docs, rerank_status = generation_service.convert_hits_to_documents(hits, question)

        assert docs == []
        assert rerank_status is False

    def test_prepare_generation_context(self, generation_service):
        """Test prepare_generation_context wrapper method"""
        hits = [
            (0, 0.85, 0.9),
            (1, 0.75, 0.85),
        ]
        question = "test question"

        docs, rerank_status = generation_service.prepare_generation_context(hits, question)

        # Should produce same result as convert_hits_to_documents
        assert len(docs) == 2
        assert rerank_status is True
        assert docs[0]["rank"] == 1
        assert docs[0]["ce_score"] == 0.9

    def test_prepare_from_domain_documents_basic(self, generation_service):
        """Test converting domain Document objects to generation format"""
        domain_docs = [
            Document(
                post_id="1",
                chunk_id=0,
                title="WordPress Security",
                url="https://example.com/security",
                chunk="Security content",
                hybrid_score=0.85,
                rank=1,
            ),
            Document(
                post_id="2",
                chunk_id=0,
                title="SEO Tips",
                url="https://example.com/seo",
                chunk="SEO content",
                hybrid_score=0.75,
                rank=2,
            ),
        ]

        result = generation_service.prepare_from_domain_documents(domain_docs)

        assert len(result) == 2
        assert result[0]["rank"] == 1
        assert result[0]["hybrid_score"] == 0.85
        assert result[0]["post_id"] == "1"
        assert result[0]["chunk_id"] == 0
        assert result[0]["title"] == "WordPress Security"
        assert result[0]["url"] == "https://example.com/security"
        assert result[0]["snippet"] == "Security content"
        assert result[0]["chunk"] == "Security content"
        assert "ce_score" not in result[0]

    def test_prepare_from_domain_documents_with_ce_score(self, generation_service):
        """Test converting domain documents with ce_score"""
        domain_docs = [
            Document(
                post_id="1",
                chunk_id=0,
                title="Test",
                url="https://example.com",
                chunk="Content",
                hybrid_score=0.8,
                ce_score=0.95,
                rank=1,
            )
        ]

        result = generation_service.prepare_from_domain_documents(domain_docs)

        assert len(result) == 1
        assert result[0]["ce_score"] == 0.95

    def test_prepare_from_domain_documents_snippet_uses_document_method(self, generation_service):
        """Test that snippet uses Document's create_snippet method"""
        long_content = "a" * 500
        domain_docs = [
            Document(
                post_id="1",
                chunk_id=0,
                title="Test",
                url="https://example.com",
                chunk=long_content,
                hybrid_score=0.8,
                rank=1,
            )
        ]

        result = generation_service.prepare_from_domain_documents(domain_docs)

        # Document.create_snippet() uses default max_length=400
        assert len(result[0]["snippet"]) == 401
        assert result[0]["snippet"].endswith("…")
        assert len(result[0]["chunk"]) == 500

    def test_prepare_from_domain_documents_empty_list(self, generation_service):
        """Test converting empty list of domain documents"""
        result = generation_service.prepare_from_domain_documents([])
        assert result == []

    def test_prepare_from_domain_documents_none_rank(self, generation_service):
        """Test converting domain documents with None rank"""
        domain_docs = [
            Document(
                post_id="1",
                chunk_id=0,
                title="Test",
                url="https://example.com",
                chunk="Content",
                hybrid_score=0.8,
                rank=None,  # None rank
            )
        ]

        result = generation_service.prepare_from_domain_documents(domain_docs)

        assert len(result) == 1
        assert result[0]["rank"] is None


class TestGenerationServiceEdgeCases:
    """Test edge cases for GenerationService"""

    def test_empty_meta(self):
        """Test service with empty metadata"""
        service = GenerationService(meta=[])
        hits = [(0, 0.85)]
        docs, _ = service.convert_hits_to_documents(hits, "test")
        assert docs == []  # All indices will be out of range

    def test_unicode_content(self, generation_service):
        """Test handling unicode content in snippets"""
        text = "日本語のコンテンツです。" * 50  # Long unicode text
        snippet = generation_service._create_snippet(text, max_length=100)
        assert len(snippet) <= 101
        assert snippet.endswith("…")

    def test_all_hits_invalid_indices(self, generation_service):
        """Test when all hits have invalid indices"""
        hits = [
            (-1, 0.9),
            (100, 0.8),
            (-5, 0.7),
        ]
        docs, rerank_status = generation_service.convert_hits_to_documents(hits, "test")
        assert docs == []
        assert rerank_status is False

    def test_mixed_hit_formats(self, generation_service):
        """Test handling mixed 2-tuple and 3-tuple hit formats"""
        # This shouldn't happen in practice, but test robustness
        hits = [
            (0, 0.85),  # 2-tuple
            (1, 0.75, 0.9),  # 3-tuple with ce_score
        ]
        docs, rerank_status = generation_service.convert_hits_to_documents(hits, "test")
        assert len(docs) == 2
        assert rerank_status is True  # Because second hit has ce_score
        assert "ce_score" not in docs[0]
        assert docs[1]["ce_score"] == 0.9

    def test_zero_scores(self, generation_service):
        """Test handling zero scores"""
        hits = [(0, 0.0, 0.0)]
        docs, rerank_status = generation_service.convert_hits_to_documents(hits, "test")
        assert len(docs) == 1
        assert docs[0]["hybrid_score"] == 0.0
        assert docs[0]["ce_score"] == 0.0

    def test_very_high_scores(self, generation_service):
        """Test handling very high scores"""
        hits = [(0, 100.0, 200.0)]
        docs, rerank_status = generation_service.convert_hits_to_documents(hits, "test")
        assert docs[0]["hybrid_score"] == 100.0
        assert docs[0]["ce_score"] == 200.0

    def test_empty_chunk_snippet(self, generation_service):
        """Test snippet creation with empty chunk"""
        snippet = generation_service._create_snippet("", max_length=400)
        assert snippet == ""

    def test_prepare_from_domain_documents_all_fields_present(self, generation_service):
        """Test that all expected fields are present in output"""
        domain_docs = [
            Document(
                post_id="123",
                chunk_id=5,
                title="Full Test",
                url="https://example.com/full",
                chunk="Complete content",
                hybrid_score=0.88,
                ce_score=0.92,
                rank=3,
            )
        ]

        result = generation_service.prepare_from_domain_documents(domain_docs)
        doc = result[0]

        # Verify all expected fields
        expected_fields = {
            "rank",
            "hybrid_score",
            "post_id",
            "chunk_id",
            "title",
            "url",
            "snippet",
            "chunk",
            "ce_score",
        }
        assert set(doc.keys()) == expected_fields
        assert doc["rank"] == 3
        assert doc["hybrid_score"] == 0.88
        assert doc["ce_score"] == 0.92
