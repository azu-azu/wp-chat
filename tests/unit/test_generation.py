# tests/unit/test_generation.py - Tests for generation.py
from unittest.mock import patch

from src.generation.generation import GenerationPipeline
from src.generation.prompts import build_messages


class TestGenerationPipeline:
    """Test GenerationPipeline functionality"""

    def test_initialization(self):
        """Test pipeline initialization"""
        with patch("src.generation.generation.get_config_value") as mock_get:
            mock_get.side_effect = lambda key, default: default
            pipeline = GenerationPipeline()
            assert pipeline.context_composer is not None
            assert pipeline.citation_processor is not None

    def test_process_retrieval_results(self):
        """Test retrieval results processing"""
        with patch("src.generation.generation.get_config_value") as mock_get:
            mock_get.side_effect = lambda key, default: default
            pipeline = GenerationPipeline()

        docs = [
            {
                "rank": 1,
                "title": "Test Article",
                "url": "https://example.com/test",
                "chunk": "This is test content.",
                "hybrid_score": 0.95,
            }
        ]

        processed_docs, metadata = pipeline.process_retrieval_results(docs)

        assert len(processed_docs) > 0
        assert "chunks_used" in metadata
        assert "total_tokens" in metadata

    def test_build_prompt(self):
        """Test prompt building"""
        with patch("src.generation.generation.get_config_value") as mock_get:
            mock_get.side_effect = lambda key, default: default
            pipeline = GenerationPipeline()

        question = "VBAで文字列処理する方法を教えて"
        docs = [
            {
                "rank": 1,
                "title": "VBA文字列処理",
                "url": "https://example.com/vba",
                "chunk": "VBAでは文字列を操作できます。",
                "citation_id": 1,
            }
        ]

        messages, stats = pipeline.build_prompt(question, docs)

        assert len(messages) > 0
        assert "total_tokens" in stats or "context_tokens" in stats
        assert any(question in str(msg) for msg in messages)

    def test_post_process_response(self):
        """Test response post-processing"""
        with patch("src.generation.generation.get_config_value") as mock_get:
            mock_get.side_effect = lambda key, default: default
            pipeline = GenerationPipeline()

        raw_response = "VBAでは文字列を操作できます。[[1]]"
        docs = [
            {
                "rank": 1,
                "title": "VBA文字列処理",
                "url": "https://example.com/vba",
                "citation_id": 1,
            }
        ]

        result = pipeline.post_process_response(raw_response, docs)

        assert result.answer == raw_response
        assert len(result.references) > 0
        assert result.metadata["has_citations"] is True
        assert result.metadata["citation_count"] > 0

    def test_generate_fallback_response(self):
        """Test fallback response generation"""
        with patch("src.generation.generation.get_config_value") as mock_get:
            mock_get.side_effect = lambda key, default: default
            pipeline = GenerationPipeline()

        question = "テスト質問"
        docs = [
            {
                "rank": 1,
                "title": "Test",
                "url": "https://example.com/test",
                "chunk": "Test content",
            }
        ]

        result = pipeline.generate_fallback_response(question, docs)

        assert result.answer is not None
        assert len(result.answer) > 0
        assert "申し訳" in result.answer or "情報" in result.answer


class TestPromptFunctions:
    """Test prompt building functions"""

    def test_build_messages_basic(self):
        """Test basic message building"""
        question = "テスト質問"
        context_chunks = [
            {"citation_id": 1, "title": "記事1", "chunk": "内容1"},
            {"citation_id": 2, "title": "記事2", "chunk": "内容2"},
        ]

        messages = build_messages(question, context_chunks)

        assert len(messages) >= 2  # システムメッセージ + ユーザーメッセージ
        assert any(question in str(msg) for msg in messages)

    def test_build_messages_with_citations(self):
        """Test message building with citation markers"""
        question = "VBAについて"
        context_chunks = [
            {"citation_id": 1, "title": "VBA基礎", "chunk": "VBAの基本"},
        ]

        messages = build_messages(question, context_chunks)

        # Check citation format [[1]]
        message_text = str(messages)
        assert "[[1]]" in message_text or "citation" in message_text.lower()
