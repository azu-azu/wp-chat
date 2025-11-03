"""
Unit tests for Document domain model
"""


from wp_chat.domain.models import Document


class TestDocument:
    """Test suite for Document domain model"""

    def test_create_valid_document(self):
        """Test creating a valid document"""
        doc = Document(
            post_id="123",
            chunk_id=0,
            title="Test Document",
            url="https://example.com/test",
            chunk="This is test content",
            hybrid_score=0.85,
        )
        assert doc.post_id == "123"
        assert doc.chunk_id == 0
        assert doc.title == "Test Document"
        assert doc.url == "https://example.com/test"
        assert doc.chunk == "This is test content"
        assert doc.hybrid_score == 0.85
        assert doc.ce_score is None
        assert doc.rank is None

    def test_create_document_with_ce_score(self):
        """Test creating document with cross-encoder score"""
        doc = Document(
            post_id="123",
            chunk_id=0,
            title="Test",
            url="https://example.com",
            chunk="content",
            hybrid_score=0.7,
            ce_score=0.9,
        )
        assert doc.ce_score == 0.9

    def test_create_document_with_rank(self):
        """Test creating document with rank"""
        doc = Document(
            post_id="123",
            chunk_id=0,
            title="Test",
            url="https://example.com",
            chunk="content",
            hybrid_score=0.7,
            rank=1,
        )
        assert doc.rank == 1

    def test_document_is_relevant_default_threshold(self):
        """Test relevance check with default threshold (0.7)"""
        relevant_doc = Document(
            post_id="123",
            chunk_id=0,
            title="Test",
            url="https://example.com",
            chunk="content",
            hybrid_score=0.75,
        )
        not_relevant_doc = Document(
            post_id="456",
            chunk_id=0,
            title="Test",
            url="https://example.com",
            chunk="content",
            hybrid_score=0.65,
        )
        assert relevant_doc.is_relevant() is True
        assert not_relevant_doc.is_relevant() is False

    def test_document_is_relevant_custom_threshold(self):
        """Test relevance check with custom threshold"""
        doc = Document(
            post_id="123",
            chunk_id=0,
            title="Test",
            url="https://example.com",
            chunk="content",
            hybrid_score=0.75,
        )
        assert doc.is_relevant(threshold=0.7) is True
        assert doc.is_relevant(threshold=0.8) is False

    def test_document_is_highly_relevant(self):
        """Test high relevance check (default threshold 0.85)"""
        highly_relevant = Document(
            post_id="123",
            chunk_id=0,
            title="Test",
            url="https://example.com",
            chunk="content",
            hybrid_score=0.9,
        )
        not_highly_relevant = Document(
            post_id="456",
            chunk_id=0,
            title="Test",
            url="https://example.com",
            chunk="content",
            hybrid_score=0.8,
        )
        assert highly_relevant.is_highly_relevant() is True
        assert not_highly_relevant.is_highly_relevant() is False

    def test_document_has_rerank_score(self):
        """Test checking if document has rerank score"""
        with_rerank = Document(
            post_id="123",
            chunk_id=0,
            title="Test",
            url="https://example.com",
            chunk="content",
            hybrid_score=0.7,
            ce_score=0.9,
        )
        without_rerank = Document(
            post_id="456",
            chunk_id=0,
            title="Test",
            url="https://example.com",
            chunk="content",
            hybrid_score=0.7,
        )
        assert with_rerank.has_rerank_score() is True
        assert without_rerank.has_rerank_score() is False

    def test_document_get_effective_score_without_rerank(self):
        """Test getting effective score when no rerank score"""
        doc = Document(
            post_id="123",
            chunk_id=0,
            title="Test",
            url="https://example.com",
            chunk="content",
            hybrid_score=0.75,
        )
        assert doc.get_effective_score() == 0.75

    def test_document_get_effective_score_with_rerank(self):
        """Test getting effective score when rerank score exists"""
        doc = Document(
            post_id="123",
            chunk_id=0,
            title="Test",
            url="https://example.com",
            chunk="content",
            hybrid_score=0.75,
            ce_score=0.9,
        )
        assert doc.get_effective_score() == 0.9

    def test_document_create_snippet_short_content(self):
        """Test creating snippet from short content"""
        doc = Document(
            post_id="123",
            chunk_id=0,
            title="Test",
            url="https://example.com",
            chunk="Short content",
            hybrid_score=0.7,
        )
        snippet = doc.create_snippet(max_length=400)
        assert snippet == "Short content"

    def test_document_create_snippet_long_content(self):
        """Test creating snippet from long content"""
        long_content = "a" * 500
        doc = Document(
            post_id="123",
            chunk_id=0,
            title="Test",
            url="https://example.com",
            chunk=long_content,
            hybrid_score=0.7,
        )
        snippet = doc.create_snippet(max_length=400)
        assert len(snippet) == 401  # 400 + "…"
        assert snippet.endswith("…")
        assert snippet[:-1] == "a" * 400

    def test_document_create_snippet_custom_length(self):
        """Test creating snippet with custom max length"""
        content = "a" * 200
        doc = Document(
            post_id="123",
            chunk_id=0,
            title="Test",
            url="https://example.com",
            chunk=content,
            hybrid_score=0.7,
        )
        snippet = doc.create_snippet(max_length=100)
        assert len(snippet) == 101  # 100 + "…"
        assert snippet.endswith("…")

    def test_document_to_dict_minimal(self):
        """Test converting document to dict (minimal fields)"""
        doc = Document(
            post_id="123",
            chunk_id=0,
            title="Test Document",
            url="https://example.com/test",
            chunk="Test content",
            hybrid_score=0.85,
        )
        result = doc.to_dict()
        assert result == {
            "post_id": "123",
            "chunk_id": 0,
            "title": "Test Document",
            "url": "https://example.com/test",
            "chunk": "Test content",
            "hybrid_score": 0.85,
        }

    def test_document_to_dict_with_rank(self):
        """Test converting document to dict with rank"""
        doc = Document(
            post_id="123",
            chunk_id=0,
            title="Test",
            url="https://example.com",
            chunk="content",
            hybrid_score=0.85,
            rank=1,
        )
        result = doc.to_dict()
        assert "rank" in result
        assert result["rank"] == 1

    def test_document_to_dict_with_ce_score(self):
        """Test converting document to dict with CE score"""
        doc = Document(
            post_id="123",
            chunk_id=0,
            title="Test",
            url="https://example.com",
            chunk="content",
            hybrid_score=0.75,
            ce_score=0.9,
        )
        result = doc.to_dict()
        assert "ce_score" in result
        assert result["ce_score"] == 0.9

    def test_document_to_dict_complete(self):
        """Test converting document to dict with all fields"""
        doc = Document(
            post_id="123",
            chunk_id=0,
            title="Test",
            url="https://example.com",
            chunk="content",
            hybrid_score=0.75,
            ce_score=0.9,
            rank=1,
        )
        result = doc.to_dict()
        assert result["rank"] == 1
        assert result["ce_score"] == 0.9
        assert result["hybrid_score"] == 0.75

    def test_document_from_meta(self):
        """Test creating document from metadata"""
        meta = {
            "post_id": "123",
            "chunk_id": 0,
            "title": "Test Document",
            "url": "https://example.com/test",
            "chunk": "Test content",
        }
        doc = Document.from_meta(meta=meta, hybrid_score=0.85)
        assert doc.post_id == "123"
        assert doc.chunk_id == 0
        assert doc.title == "Test Document"
        assert doc.url == "https://example.com/test"
        assert doc.chunk == "Test content"
        assert doc.hybrid_score == 0.85
        assert doc.ce_score is None
        assert doc.rank is None

    def test_document_from_meta_with_ce_score_and_rank(self):
        """Test creating document from metadata with optional fields"""
        meta = {
            "post_id": "123",
            "chunk_id": 0,
            "title": "Test",
            "url": "https://example.com",
            "chunk": "content",
        }
        doc = Document.from_meta(
            meta=meta,
            hybrid_score=0.75,
            ce_score=0.9,
            rank=1,
        )
        assert doc.hybrid_score == 0.75
        assert doc.ce_score == 0.9
        assert doc.rank == 1


class TestDocumentEdgeCases:
    """Test edge cases for Document model"""

    def test_document_with_integer_post_id(self):
        """Test document with integer post_id (converted to string)"""
        doc = Document(
            post_id=123,  # Will be stored as is (dataclass doesn't auto-convert)
            chunk_id=0,
            title="Test",
            url="https://example.com",
            chunk="content",
            hybrid_score=0.7,
        )
        # post_id type is determined by input - no automatic conversion in dataclass
        assert doc.post_id == 123

    def test_document_with_empty_chunk(self):
        """Test document with empty chunk"""
        doc = Document(
            post_id="123",
            chunk_id=0,
            title="Test",
            url="https://example.com",
            chunk="",
            hybrid_score=0.7,
        )
        assert doc.chunk == ""
        assert doc.create_snippet() == ""

    def test_document_with_unicode_content(self):
        """Test document with Unicode content"""
        doc = Document(
            post_id="123",
            chunk_id=0,
            title="日本語タイトル",
            url="https://example.com",
            chunk="これは日本語のコンテンツです。",
            hybrid_score=0.7,
        )
        assert doc.title == "日本語タイトル"
        assert doc.chunk == "これは日本語のコンテンツです。"

    def test_document_with_zero_hybrid_score(self):
        """Test document with zero hybrid score"""
        doc = Document(
            post_id="123",
            chunk_id=0,
            title="Test",
            url="https://example.com",
            chunk="content",
            hybrid_score=0.0,
        )
        assert doc.hybrid_score == 0.0
        assert doc.is_relevant() is False
        assert doc.get_effective_score() == 0.0

    def test_document_with_max_hybrid_score(self):
        """Test document with maximum hybrid score (1.0)"""
        doc = Document(
            post_id="123",
            chunk_id=0,
            title="Test",
            url="https://example.com",
            chunk="content",
            hybrid_score=1.0,
        )
        assert doc.hybrid_score == 1.0
        assert doc.is_relevant() is True
        assert doc.is_highly_relevant() is True
