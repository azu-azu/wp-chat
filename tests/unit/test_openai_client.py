# tests/unit/test_openai_client.py - Tests for openai_client.py
import os
from unittest.mock import Mock, patch

import pytest

from wp_chat.generation.openai_client import GenerationMetrics, OpenAIClient


class TestOpenAIClient:
    """Test OpenAIClient functionality"""

    @pytest.fixture
    def client(self):
        """Create OpenAI client for testing"""
        # Mock environment and config
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch("wp_chat.generation.openai_client.load_config") as mock_config:
                mock_config.return_value = {
                    "models": {
                        "default-mini": {
                            "name": "gpt-4o-mini",
                            "temperature": 0.7,
                            "max_tokens": 1000,
                            "description": "Test model",
                        }
                    },
                    "llm": {"alias": "default-mini", "timeout_sec": 30},
                }
                with patch("wp_chat.generation.openai_client.get_config_value") as mock_get:
                    mock_get.side_effect = lambda key, default=None: {
                        "llm.alias": "default-mini",
                        "llm.timeout_sec": 30,
                    }.get(key, default)
                    return OpenAIClient()

    def test_initialization(self, client):
        """Test client initialization"""
        assert client.config is not None
        assert client.model_name is not None
        assert client.timeout_sec > 0

    @pytest.mark.asyncio
    async def test_chat_completion_success(self, client, mock_openai_response):
        """Test successful chat completion"""
        messages = [{"role": "user", "content": "Test question"}]

        with patch.object(
            client.client.chat.completions, "create", return_value=mock_openai_response
        ):
            content, metrics = await client.chat_completion(messages)

            assert content is not None
            assert isinstance(metrics, GenerationMetrics)
            assert metrics.success is True
            assert metrics.total_latency_ms > 0

    @pytest.mark.asyncio
    async def test_chat_completion_error(self, client):
        """Test chat completion with error"""
        messages = [{"role": "user", "content": "Test question"}]

        with patch.object(
            client.client.chat.completions, "create", side_effect=Exception("API Error")
        ):
            content, metrics = await client.chat_completion(messages)

            assert metrics.success is False
            assert metrics.error_message is not None

    @pytest.mark.asyncio
    async def test_stream_chat_success(self, client, mock_openai_stream):
        """Test streaming chat completion"""
        messages = [{"role": "user", "content": "Test question"}]

        chunks = []
        with patch.object(
            client.client.chat.completions, "create", return_value=mock_openai_stream
        ):
            async for chunk in client.stream_chat(messages):
                chunks.append(chunk)

        # Should have delta chunks and done chunk
        assert len(chunks) > 0
        assert any(c["type"] == "delta" for c in chunks)
        assert any(c["type"] == "done" for c in chunks)

    @pytest.mark.asyncio
    async def test_stream_chat_error(self, client):
        """Test streaming with error"""
        messages = [{"role": "user", "content": "Test question"}]

        with patch.object(
            client.client.chat.completions, "create", side_effect=Exception("Stream Error")
        ):
            chunks = []
            async for chunk in client.stream_chat(messages):
                chunks.append(chunk)

            # Should have error chunk
            assert any(c["type"] == "error" for c in chunks)

    def test_get_model_info(self, client):
        """Test getting model info"""
        info = client.get_model_info()

        assert "name" in info
        assert "temperature" in info
        assert info["name"] == "gpt-4o-mini"


class TestGenerationMetrics:
    """Test GenerationMetrics dataclass"""

    def test_metrics_creation(self):
        """Test metrics creation"""
        metrics = GenerationMetrics(
            success=True,
            model="gpt-4o-mini",
            total_latency_ms=1000,
            ttft_ms=200,
            token_usage={"total_tokens": 100},
            error_message=None,
        )

        assert metrics.success is True
        assert metrics.model == "gpt-4o-mini"
        assert metrics.total_latency_ms == 1000

    def test_metrics_with_error(self):
        """Test metrics with error"""
        metrics = GenerationMetrics(
            success=False,
            model="gpt-4o-mini",
            total_latency_ms=500,
            ttft_ms=0,
            token_usage={},
            error_message="API Error",
        )

        assert metrics.success is False
        assert metrics.error_message is not None


class TestOpenAIClientConfiguration:
    """Test OpenAI client configuration"""

    def test_model_selection(self):
        """Test model selection from config"""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch("wp_chat.generation.openai_client.load_config") as mock_config:
                mock_config.return_value = {
                    "models": {
                        "default-mini": {
                            "name": "gpt-4o-mini",
                            "temperature": 0.7,
                            "max_tokens": 1000,
                        }
                    },
                    "llm": {"alias": "default-mini", "timeout_sec": 30},
                }
                with patch("wp_chat.generation.openai_client.get_config_value") as mock_get:
                    mock_get.side_effect = lambda key, default=None: {
                        "llm.alias": "default-mini",
                        "llm.timeout_sec": 30,
                    }.get(key, default)
                    client = OpenAIClient()
                    assert client.model_name in ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo"]

    def test_timeout_configuration(self):
        """Test timeout configuration"""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch("wp_chat.generation.openai_client.load_config") as mock_config:
                mock_config.return_value = {
                    "models": {
                        "default-mini": {
                            "name": "gpt-4o-mini",
                            "temperature": 0.7,
                            "max_tokens": 1000,
                        }
                    },
                    "llm": {"alias": "default-mini", "timeout_sec": 30},
                }
                with patch("wp_chat.generation.openai_client.get_config_value") as mock_get:
                    mock_get.side_effect = lambda key, default=None: {
                        "llm.alias": "default-mini",
                        "llm.timeout_sec": 30,
                    }.get(key, default)
                    client = OpenAIClient()
                    assert client.timeout_sec == 30

    def test_temperature_configuration(self):
        """Test temperature configuration"""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch("wp_chat.generation.openai_client.load_config") as mock_config:
                mock_config.return_value = {
                    "models": {
                        "default-mini": {
                            "name": "gpt-4o-mini",
                            "temperature": 0.7,
                            "max_tokens": 1000,
                        }
                    },
                    "llm": {"alias": "default-mini", "timeout_sec": 30},
                }
                with patch("wp_chat.generation.openai_client.get_config_value") as mock_get:
                    mock_get.side_effect = lambda key, default=None: {
                        "llm.alias": "default-mini",
                        "llm.timeout_sec": 30,
                    }.get(key, default)
                    client = OpenAIClient()
                    assert client.temperature == 0.7


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response"""
    response = Mock()
    response.choices = [Mock()]
    response.choices[0].message.content = "This is a test response. [[1]]"
    response.usage.total_tokens = 100
    response.usage.prompt_tokens = 50
    response.usage.completion_tokens = 50
    response.model = "gpt-4o-mini"
    return response


@pytest.fixture
def mock_openai_stream():
    """Mock OpenAI streaming response"""

    async def async_generator():
        # Delta chunks
        for text in ["This ", "is ", "a ", "test."]:
            chunk = Mock()
            chunk.choices = [Mock()]
            chunk.choices[0].delta.content = text
            chunk.choices[0].finish_reason = None
            yield chunk

        # Final chunk
        final_chunk = Mock()
        final_chunk.choices = [Mock()]
        final_chunk.choices[0].delta.content = None
        final_chunk.choices[0].finish_reason = "stop"
        yield final_chunk

    return async_generator()
