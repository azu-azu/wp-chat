"""
Unit tests for GenerationResult domain model
"""

import pytest

from wp_chat.domain.models import GenerationResult


class TestGenerationResult:
    """Test suite for GenerationResult domain model"""

    def test_create_generation_result_minimal(self):
        """Test creating a minimal generation result"""
        result = GenerationResult(answer="This is the answer")
        assert result.answer == "This is the answer"
        assert result.references == []
        assert result.metadata == {}

    def test_create_generation_result_with_references(self):
        """Test creating generation result with references"""
        refs = [
            {"title": "Doc 1", "url": "https://example.com/1"},
            {"title": "Doc 2", "url": "https://example.com/2"},
        ]
        result = GenerationResult(
            answer="Answer with references",
            references=refs,
        )
        assert len(result.references) == 2
        assert result.references[0]["title"] == "Doc 1"

    def test_create_generation_result_with_metadata(self):
        """Test creating generation result with metadata"""
        metadata = {
            "latency_ms": 250,
            "model": "gpt-4",
            "token_count": 150,
        }
        result = GenerationResult(
            answer="Answer",
            metadata=metadata,
        )
        assert result.metadata["latency_ms"] == 250
        assert result.metadata["model"] == "gpt-4"

    def test_has_citations_true(self):
        """Test has_citations returns True when citations exist"""
        result = GenerationResult(
            answer="Answer",
            metadata={"has_citations": True},
        )
        assert result.has_citations() is True

    def test_has_citations_false(self):
        """Test has_citations returns False when no citations"""
        result = GenerationResult(
            answer="Answer",
            metadata={"has_citations": False},
        )
        assert result.has_citations() is False

    def test_has_citations_missing_metadata(self):
        """Test has_citations returns False when metadata missing"""
        result = GenerationResult(answer="Answer")
        assert result.has_citations() is False

    def test_citation_count(self):
        """Test citation_count returns correct count"""
        result = GenerationResult(
            answer="Answer",
            metadata={"citation_count": 3},
        )
        assert result.citation_count() == 3

    def test_citation_count_missing_metadata(self):
        """Test citation_count returns 0 when metadata missing"""
        result = GenerationResult(answer="Answer")
        assert result.citation_count() == 0

    def test_get_latency_ms(self):
        """Test get_latency_ms returns correct value"""
        result = GenerationResult(
            answer="Answer",
            metadata={"latency_ms": 350},
        )
        assert result.get_latency_ms() == 350

    def test_get_latency_ms_missing(self):
        """Test get_latency_ms returns 0 when missing"""
        result = GenerationResult(answer="Answer")
        assert result.get_latency_ms() == 0

    def test_get_ttft_ms(self):
        """Test get_ttft_ms returns correct value"""
        result = GenerationResult(
            answer="Answer",
            metadata={"ttft_ms": 50},
        )
        assert result.get_ttft_ms() == 50

    def test_get_ttft_ms_missing(self):
        """Test get_ttft_ms returns 0 when missing"""
        result = GenerationResult(answer="Answer")
        assert result.get_ttft_ms() == 0

    def test_get_token_count(self):
        """Test get_token_count returns correct value"""
        result = GenerationResult(
            answer="Answer",
            metadata={"token_count": 200},
        )
        assert result.get_token_count() == 200

    def test_get_token_count_missing(self):
        """Test get_token_count returns 0 when missing"""
        result = GenerationResult(answer="Answer")
        assert result.get_token_count() == 0

    def test_get_model(self):
        """Test get_model returns correct model name"""
        result = GenerationResult(
            answer="Answer",
            metadata={"model": "gpt-4"},
        )
        assert result.get_model() == "gpt-4"

    def test_get_model_missing(self):
        """Test get_model returns 'unknown' when missing"""
        result = GenerationResult(answer="Answer")
        assert result.get_model() == "unknown"

    def test_is_fallback_true(self):
        """Test is_fallback returns True when fallback flag set"""
        result = GenerationResult(
            answer="Fallback answer",
            metadata={"fallback": True},
        )
        assert result.is_fallback() is True

    def test_is_fallback_false(self):
        """Test is_fallback returns False when not fallback"""
        result = GenerationResult(
            answer="Normal answer",
            metadata={"fallback": False},
        )
        assert result.is_fallback() is False

    def test_is_fallback_missing(self):
        """Test is_fallback returns False when metadata missing"""
        result = GenerationResult(answer="Answer")
        assert result.is_fallback() is False

    def test_has_error_true(self):
        """Test has_error returns True when error message exists"""
        result = GenerationResult(
            answer="Answer",
            metadata={"error_message": "Something went wrong"},
        )
        assert result.has_error() is True

    def test_has_error_false(self):
        """Test has_error returns False when no error"""
        result = GenerationResult(answer="Answer")
        assert result.has_error() is False

    def test_get_error_message(self):
        """Test get_error_message returns error message"""
        result = GenerationResult(
            answer="Answer",
            metadata={"error_message": "Timeout error"},
        )
        assert result.get_error_message() == "Timeout error"

    def test_get_error_message_none(self):
        """Test get_error_message returns None when no error"""
        result = GenerationResult(answer="Answer")
        assert result.get_error_message() is None

    def test_reference_count(self):
        """Test reference_count returns correct count"""
        refs = [
            {"title": "Doc 1", "url": "https://example.com/1"},
            {"title": "Doc 2", "url": "https://example.com/2"},
            {"title": "Doc 3", "url": "https://example.com/3"},
        ]
        result = GenerationResult(answer="Answer", references=refs)
        assert result.reference_count() == 3

    def test_reference_count_empty(self):
        """Test reference_count returns 0 when no references"""
        result = GenerationResult(answer="Answer")
        assert result.reference_count() == 0

    def test_get_unique_sources(self):
        """Test get_unique_sources returns unique URLs"""
        refs = [
            {"title": "Doc 1", "url": "https://example.com/page1"},
            {"title": "Doc 2", "url": "https://example.com/page2"},
            {"title": "Doc 3", "url": "https://example.com/page1"},  # Duplicate
        ]
        result = GenerationResult(answer="Answer", references=refs)
        unique = result.get_unique_sources()
        assert len(unique) == 2
        assert "https://example.com/page1" in unique
        assert "https://example.com/page2" in unique

    def test_get_unique_sources_with_missing_urls(self):
        """Test get_unique_sources handles references without URLs"""
        refs = [
            {"title": "Doc 1", "url": "https://example.com/page1"},
            {"title": "Doc 2"},  # No URL
            {"title": "Doc 3", "url": "https://example.com/page2"},
        ]
        result = GenerationResult(answer="Answer", references=refs)
        unique = result.get_unique_sources()
        assert len(unique) == 2
        assert "https://example.com/page1" in unique
        assert "https://example.com/page2" in unique

    def test_get_unique_sources_empty(self):
        """Test get_unique_sources returns empty set when no references"""
        result = GenerationResult(answer="Answer")
        assert len(result.get_unique_sources()) == 0

    def test_calculate_answer_quality_score_fallback(self):
        """Test quality score for fallback result"""
        result = GenerationResult(
            answer="Fallback answer",
            metadata={"fallback": True},
        )
        score = result.calculate_answer_quality_score()
        assert score == 0.3

    def test_calculate_answer_quality_score_with_error(self):
        """Test quality score for result with error"""
        result = GenerationResult(
            answer="Answer",
            metadata={"error_message": "Error occurred"},
        )
        score = result.calculate_answer_quality_score()
        assert score == 0.3

    def test_calculate_answer_quality_score_base(self):
        """Test quality score with no citations or references"""
        result = GenerationResult(answer="Answer")
        score = result.calculate_answer_quality_score()
        assert score == 0.5

    def test_calculate_answer_quality_score_with_citations(self):
        """Test quality score with citations"""
        result = GenerationResult(
            answer="Answer",
            metadata={"has_citations": True, "citation_count": 3},
        )
        score = result.calculate_answer_quality_score()
        # 0.5 + 0.3 * (3/5) = 0.5 + 0.18 = 0.68
        assert score == pytest.approx(0.68)

    def test_calculate_answer_quality_score_with_max_citations(self):
        """Test quality score with max citations (5+)"""
        result = GenerationResult(
            answer="Answer",
            metadata={"has_citations": True, "citation_count": 7},
        )
        score = result.calculate_answer_quality_score()
        # 0.5 + 0.3 * 1.0 = 0.8
        assert score == 0.8

    def test_calculate_answer_quality_score_with_references(self):
        """Test quality score with references"""
        refs = [
            {"title": "Doc 1", "url": "https://example.com/1"},
            {"title": "Doc 2", "url": "https://example.com/2"},
        ]
        result = GenerationResult(answer="Answer", references=refs)
        score = result.calculate_answer_quality_score()
        # 0.5 + 0.2 * (2/3) = 0.5 + 0.133... ≈ 0.633
        assert score == pytest.approx(0.633, abs=0.01)

    def test_calculate_answer_quality_score_with_max_references(self):
        """Test quality score with max references (3+)"""
        refs = [{"title": f"Doc {i}", "url": f"https://example.com/{i}"} for i in range(5)]
        result = GenerationResult(answer="Answer", references=refs)
        score = result.calculate_answer_quality_score()
        # 0.5 + 0.2 * 1.0 = 0.7
        assert score == 0.7

    def test_calculate_answer_quality_score_perfect(self):
        """Test quality score with both max citations and references"""
        refs = [{"title": f"Doc {i}", "url": f"https://example.com/{i}"} for i in range(3)]
        result = GenerationResult(
            answer="Answer",
            references=refs,
            metadata={"has_citations": True, "citation_count": 5},
        )
        score = result.calculate_answer_quality_score()
        # 0.5 + 0.3 + 0.2 = 1.0
        assert score == 1.0

    def test_to_dict_minimal(self):
        """Test converting generation result to dict (minimal)"""
        result = GenerationResult(answer="Test answer")
        result_dict = result.to_dict()
        assert result_dict["answer"] == "Test answer"
        assert result_dict["references"] == []
        assert result_dict["metadata"] == {}

    def test_to_dict_complete(self):
        """Test converting generation result to dict (complete)"""
        refs = [{"title": "Doc", "url": "https://example.com"}]
        metadata = {
            "latency_ms": 200,
            "model": "gpt-4",
            "has_citations": True,
        }
        result = GenerationResult(
            answer="Complete answer",
            references=refs,
            metadata=metadata,
        )
        result_dict = result.to_dict()
        assert result_dict["answer"] == "Complete answer"
        assert len(result_dict["references"]) == 1
        assert result_dict["metadata"]["latency_ms"] == 200
        assert result_dict["metadata"]["model"] == "gpt-4"

    def test_create_success(self):
        """Test create_success factory method"""
        refs = [{"title": "Doc", "url": "https://example.com"}]
        result = GenerationResult.create_success(
            answer="Success answer",
            references=refs,
            latency_ms=300,
            ttft_ms=50,
            token_count=180,
            model="gpt-4",
            citation_count=3,
            has_citations=True,
        )

        assert result.answer == "Success answer"
        assert len(result.references) == 1
        assert result.get_latency_ms() == 300
        assert result.get_ttft_ms() == 50
        assert result.get_token_count() == 180
        assert result.get_model() == "gpt-4"
        assert result.citation_count() == 3
        assert result.has_citations() is True
        assert result.is_fallback() is False

    def test_create_success_with_extra_metadata(self):
        """Test create_success with extra metadata fields"""
        result = GenerationResult.create_success(
            answer="Answer",
            references=[],
            latency_ms=200,
            ttft_ms=30,
            token_count=100,
            model="gpt-3.5",
            citation_count=2,
            has_citations=True,
            custom_field="custom_value",
            version="1.0",
        )

        assert result.metadata["custom_field"] == "custom_value"
        assert result.metadata["version"] == "1.0"

    def test_create_fallback(self):
        """Test create_fallback factory method"""
        refs = [{"title": "Doc", "url": "https://example.com"}]
        result = GenerationResult.create_fallback(
            answer="Fallback answer",
            references=refs,
            error_message="Generation timeout",
            latency_ms=5000,
        )

        assert result.answer == "Fallback answer"
        assert len(result.references) == 1
        assert result.is_fallback() is True
        assert result.has_error() is True
        assert result.get_error_message() == "Generation timeout"
        assert result.get_latency_ms() == 5000
        assert result.get_ttft_ms() == 0
        assert result.get_token_count() == 0
        assert result.get_model() == "fallback"
        assert result.citation_count() == 0
        assert result.has_citations() is False

    def test_create_fallback_with_extra_metadata(self):
        """Test create_fallback with extra metadata fields"""
        result = GenerationResult.create_fallback(
            answer="Fallback answer",
            references=[],
            error_message="Error",
            error_code=500,
            retry_count=3,
        )

        assert result.metadata["error_code"] == 500
        assert result.metadata["retry_count"] == 3


class TestGenerationResultEdgeCases:
    """Test edge cases for GenerationResult model"""

    def test_empty_answer(self):
        """Test generation result with empty answer"""
        result = GenerationResult(answer="")
        assert result.answer == ""
        assert result.reference_count() == 0

    def test_very_long_answer(self):
        """Test generation result with very long answer"""
        long_answer = "a" * 10000
        result = GenerationResult(answer=long_answer)
        assert len(result.answer) == 10000

    def test_unicode_in_answer(self):
        """Test generation result with unicode content"""
        result = GenerationResult(
            answer="日本語の回答です。これはテストです。",
            references=[{"title": "日本語タイトル", "url": "https://example.com"}],
        )
        assert result.answer == "日本語の回答です。これはテストです。"
        assert result.references[0]["title"] == "日本語タイトル"

    def test_special_characters_in_answer(self):
        """Test generation result with special characters"""
        answer = 'Answer with <html>, "quotes", and symbols: @#$%^&*()'
        result = GenerationResult(answer=answer)
        assert result.answer == answer

    def test_zero_metrics(self):
        """Test generation result with zero metrics"""
        result = GenerationResult(
            answer="Answer",
            metadata={
                "latency_ms": 0,
                "ttft_ms": 0,
                "token_count": 0,
                "citation_count": 0,
            },
        )
        assert result.get_latency_ms() == 0
        assert result.get_ttft_ms() == 0
        assert result.get_token_count() == 0
        assert result.citation_count() == 0

    def test_negative_metrics_handling(self):
        """Test handling of negative metrics (edge case)"""
        # While this shouldn't happen in production, test it doesn't crash
        result = GenerationResult(
            answer="Answer",
            metadata={
                "latency_ms": -100,
                "citation_count": -5,
            },
        )
        # Values are returned as-is (no validation in getter methods)
        assert result.get_latency_ms() == -100
        assert result.citation_count() == -5

    def test_extremely_high_metrics(self):
        """Test handling of very large metrics"""
        result = GenerationResult(
            answer="Answer",
            metadata={
                "latency_ms": 1000000,
                "token_count": 50000,
                "citation_count": 100,
            },
        )
        assert result.get_latency_ms() == 1000000
        assert result.get_token_count() == 50000
        assert result.citation_count() == 100

    def test_references_with_various_fields(self):
        """Test references with various field combinations"""
        refs = [
            {"title": "Doc 1", "url": "https://example.com/1", "score": 0.9},
            {"title": "Doc 2", "url": "https://example.com/2"},
            {"url": "https://example.com/3"},  # No title
            {"title": "Doc 4"},  # No URL
        ]
        result = GenerationResult(answer="Answer", references=refs)
        assert result.reference_count() == 4
        unique_sources = result.get_unique_sources()
        assert len(unique_sources) == 3  # 3 refs have URLs

    def test_quality_score_edge_cases(self):
        """Test quality score calculation edge cases"""
        # Zero citations and references
        result1 = GenerationResult(
            answer="Answer",
            metadata={"has_citations": True, "citation_count": 0},
        )
        assert result1.calculate_answer_quality_score() == 0.5

        # Very high citation count
        result2 = GenerationResult(
            answer="Answer",
            metadata={"has_citations": True, "citation_count": 100},
        )
        score = result2.calculate_answer_quality_score()
        assert score == 0.8  # Should cap at max

    def test_quality_score_combined_penalties(self):
        """Test quality score when both fallback and error are present"""
        result = GenerationResult(
            answer="Answer",
            metadata={"fallback": True, "error_message": "Error"},
        )
        # Should still return 0.3 (not 0.3 twice)
        assert result.calculate_answer_quality_score() == 0.3

    def test_metadata_type_safety(self):
        """Test that various metadata types don't cause issues"""
        metadata = {
            "string_field": "value",
            "int_field": 123,
            "float_field": 45.67,
            "bool_field": True,
            "list_field": [1, 2, 3],
            "dict_field": {"nested": "value"},
        }
        result = GenerationResult(answer="Answer", metadata=metadata)
        result_dict = result.to_dict()
        assert result_dict["metadata"]["string_field"] == "value"
        assert result_dict["metadata"]["int_field"] == 123
        assert result_dict["metadata"]["bool_field"] is True

    def test_create_success_minimal_parameters(self):
        """Test create_success with minimal required parameters"""
        result = GenerationResult.create_success(
            answer="Answer",
            references=[],
            latency_ms=100,
            ttft_ms=20,
            token_count=50,
            model="test-model",
            citation_count=0,
            has_citations=False,
        )
        assert result.answer == "Answer"
        assert result.is_fallback() is False
        assert not result.has_error()

    def test_create_fallback_default_latency(self):
        """Test create_fallback with default latency"""
        result = GenerationResult.create_fallback(
            answer="Fallback",
            references=[],
            error_message="Error",
        )
        assert result.get_latency_ms() == 0
        assert result.is_fallback() is True
