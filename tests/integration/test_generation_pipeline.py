# tests/integration/test_generation_pipeline.py
# Integration tests for RAG generation pipeline (migrated from test_mvp4.py)
import os

import pytest


@pytest.mark.integration
class TestGenerationPipeline:
    """Integration tests for RAG generation pipeline"""

    def test_imports(self):
        """Test that all modules can be imported"""
        from src.core import config
        from src.generation import generation, openai_client, prompts

        assert generation is not None
        assert prompts is not None
        assert openai_client is not None
        assert config is not None

    def test_config_loading(self):
        """Test configuration loading"""
        from src.core.config import get_config_value

        # Test LLM config
        provider = get_config_value("llm.provider")
        alias = get_config_value("llm.alias")
        model_name = get_config_value(f"models.{alias}.name")

        assert provider == "openai"
        assert alias is not None
        assert model_name is not None

        # Test generation config
        context_max = get_config_value("generation.context_max_tokens")
        citation_style = get_config_value("generation.citation_style")

        assert context_max > 0
        assert citation_style == "bracketed"

    def test_prompt_building(self, sample_documents):
        """Test prompt building"""
        from src.generation.prompts import build_messages, validate_citations

        # Build messages
        messages = build_messages("What is the main topic?", sample_documents)

        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert len(messages[0]["content"]) > 0
        assert len(messages[1]["content"]) > 0

        # Test citation validation
        test_text = "This is a test with citations [[1]] and [[2]]."
        validation = validate_citations(test_text, len(sample_documents))

        assert validation["citations"] == [1, 2]
        assert validation["citation_count"] == 2
        assert validation["is_valid"] is True

    def test_context_composition(self, sample_search_results):
        """Test context composition"""
        from src.generation.generation import ContextComposer

        composer = ContextComposer()

        # Test deduplication
        deduplicated = composer.deduplicate_by_url(sample_search_results)
        assert len(deduplicated) <= len(sample_search_results)

        # Test token estimation
        test_text = "This is a test string"
        tokens = composer.estimate_tokens(test_text)
        assert tokens > 0

    def test_openai_client_initialization(self):
        """Test OpenAI client initialization"""
        from src.core.config import get_config_value
        from src.generation.openai_client import OpenAIClient

        # Get model alias
        alias = get_config_value("llm.alias", "default-mini")

        # Initialize client (will fail if API key not set, which is okay for test)
        try:
            client = OpenAIClient(alias=alias)
            model_info = client.get_model_info()

            assert model_info["alias"] == alias
            assert model_info["name"] is not None
            assert model_info["temperature"] >= 0
            assert model_info["max_tokens"] > 0

            # Test if API key is set
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                assert len(api_key) > 0
        except ValueError as e:
            # API key not set is acceptable in test environment
            if "OPENAI_API_KEY" in str(e):
                pytest.skip("OPENAI_API_KEY not set")
            else:
                raise

    @pytest.mark.slow
    def test_full_generation_pipeline(self, sample_search_results, mock_openai_client):
        """Test full generation pipeline (mocked OpenAI)"""
        from src.generation.generation import ContextComposer
        from src.generation.prompts import build_messages, format_references

        # Prepare context
        composer = ContextComposer()
        deduplicated = composer.deduplicate_by_url(sample_search_results)

        # Build messages
        question = "VBAで文字列処理する方法を教えて"
        messages = build_messages(question, deduplicated[:3])

        assert len(messages) == 2
        assert question in messages[1]["content"]

        # Format references
        references = format_references(deduplicated[:3])

        assert len(references) == 3
        assert all("id" in ref for ref in references)
        assert all("title" in ref for ref in references)
        assert all("url" in ref for ref in references)


@pytest.mark.integration
class TestRetrievalIntegration:
    """Integration tests for retrieval → generation flow"""

    def test_search_to_generation_flow(self, sample_search_results):
        """Test search results flowing into generation"""
        from src.generation.generation import ContextComposer
        from src.generation.prompts import build_messages

        # Simulate retrieval results
        results = sample_search_results

        # Process for generation
        composer = ContextComposer()
        deduplicated = composer.deduplicate_by_url(results)

        # Build context
        question = "Test question"
        messages = build_messages(question, deduplicated)

        assert len(messages) > 0
        assert any(result["title"] in messages[1]["content"] for result in deduplicated)
