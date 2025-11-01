# tests/unit/test_config.py
import pytest

from src.core.config import get_config_value, load_config


@pytest.mark.unit
class TestConfig:
    """Unit tests for configuration management"""

    def test_load_config(self):
        """Test config loading"""
        config = load_config()

        assert config is not None
        assert isinstance(config, dict)
        assert "llm" in config
        assert "generation" in config

    def test_get_config_value_simple(self):
        """Test getting simple config value"""
        provider = get_config_value("llm.provider")

        assert provider == "openai"

    def test_get_config_value_nested(self):
        """Test getting nested config value"""
        alias = get_config_value("llm.alias")
        model_name = get_config_value(f"models.{alias}.name")

        assert model_name is not None
        assert isinstance(model_name, str)

    def test_get_config_value_with_default(self):
        """Test getting config value with default"""
        non_existent = get_config_value("non.existent.key", default="default_value")

        assert non_existent == "default_value"

    def test_get_config_value_not_found(self):
        """Test getting non-existent config value without default"""
        with pytest.raises((KeyError, ValueError)):
            get_config_value("non.existent.key")

    def test_generation_config(self):
        """Test generation configuration values"""
        context_max_tokens = get_config_value("generation.context_max_tokens")
        chunk_max_tokens = get_config_value("generation.chunk_max_tokens")
        max_chunks = get_config_value("generation.max_chunks")
        citation_style = get_config_value("generation.citation_style")

        assert context_max_tokens > 0
        assert chunk_max_tokens > 0
        assert max_chunks > 0
        assert citation_style in ["bracketed", "numbered"]

    def test_api_config(self):
        """Test API configuration values"""
        topk_default = get_config_value("api.topk_default", default=5)
        topk_max = get_config_value("api.topk_max", default=10)

        assert topk_default > 0
        assert topk_max >= topk_default

    def test_hybrid_search_config(self):
        """Test hybrid search configuration"""
        alpha = get_config_value("hybrid.alpha", default=0.6)

        assert 0.0 <= alpha <= 1.0

    def test_model_config(self):
        """Test model configuration"""
        alias = get_config_value("llm.alias")
        model_config = get_config_value(f"models.{alias}")

        assert "name" in model_config
        assert "temperature" in model_config
        assert "max_tokens" in model_config

        assert isinstance(model_config["name"], str)
        assert 0.0 <= model_config["temperature"] <= 2.0
        assert model_config["max_tokens"] > 0
