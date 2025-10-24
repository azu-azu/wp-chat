# src/openai_client.py - OpenAI client wrapper with streaming support
import os
import json
import time
import asyncio
from typing import List, Dict, Any, Optional, AsyncGenerator, Tuple
from dataclasses import dataclass
from openai import AsyncOpenAI
from .config import get_config_value, load_config

@dataclass
class TokenUsage:
    """Token usage statistics"""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

@dataclass
class GenerationMetrics:
    """Generation performance metrics"""
    ttft_ms: int  # Time to first token
    total_latency_ms: int
    token_usage: TokenUsage
    model: str
    success: bool
    error_message: Optional[str] = None

class OpenAIClient:
    """OpenAI client with streaming support and error handling"""

    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")

        self.client = AsyncOpenAI(api_key=self.api_key)
        self.config = load_config()

        # Get model configuration
        self.model_alias = get_config_value("llm.alias", "default-mini")
        self.model_config = self.config["models"][self.model_alias]
        self.model_name = self.model_config["name"]
        self.temperature = self.model_config["temperature"]
        self.max_tokens = self.model_config["max_tokens"]
        self.timeout_sec = get_config_value("llm.timeout_sec", 30)

    def get_model_info(self) -> Dict[str, Any]:
        """Get current model information"""
        return {
            "alias": self.model_alias,
            "name": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "description": self.model_config.get("description", "")
        }

    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream chat completion with error handling"""
        start_time = time.time()
        first_token_time = None
        token_usage = TokenUsage(0, 0, 0)

        try:
            # Use provided parameters or defaults
            model = model or self.model_name
            temperature = temperature or self.temperature
            max_tokens = max_tokens or self.max_tokens

            # Make API call
            response = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=True
                ),
                timeout=self.timeout_sec
            )

            # Process streaming response
            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content

                    # Record first token time
                    if first_token_time is None:
                        first_token_time = time.time()
                        ttft_ms = int((first_token_time - start_time) * 1000)
                        yield {
                            "type": "metrics",
                            "ttft_ms": ttft_ms,
                            "model": model
                        }

                    # Yield content
                    yield {
                        "type": "delta",
                        "content": content
                    }

                # Update token usage if available
                if chunk.usage:
                    token_usage = TokenUsage(
                        prompt_tokens=chunk.usage.prompt_tokens,
                        completion_tokens=chunk.usage.completion_tokens,
                        total_tokens=chunk.usage.total_tokens
                    )

            # Final metrics
            total_latency_ms = int((time.time() - start_time) * 1000)
            yield {
                "type": "done",
                "metrics": {
                    "ttft_ms": int((first_token_time - start_time) * 1000) if first_token_time else 0,
                    "total_latency_ms": total_latency_ms,
                    "token_usage": token_usage.__dict__,
                    "model": model,
                    "success": True
                }
            }

        except asyncio.TimeoutError:
            yield {
                "type": "error",
                "error": "Request timeout",
                "metrics": {
                    "ttft_ms": 0,
                    "total_latency_ms": int((time.time() - start_time) * 1000),
                    "token_usage": token_usage.__dict__,
                    "model": model,
                    "success": False,
                    "error_message": "Request timeout"
                }
            }

        except Exception as e:
            yield {
                "type": "error",
                "error": str(e),
                "metrics": {
                    "ttft_ms": 0,
                    "total_latency_ms": int((time.time() - start_time) * 1000),
                    "token_usage": token_usage.__dict__,
                    "model": model,
                    "success": False,
                    "error_message": str(e)
                }
            }

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Tuple[str, GenerationMetrics]:
        """Non-streaming chat completion"""
        start_time = time.time()
        first_token_time = None
        token_usage = TokenUsage(0, 0, 0)

        try:
            # Use provided parameters or defaults
            model = model or self.model_name
            temperature = temperature or self.temperature
            max_tokens = max_tokens or self.max_tokens

            # Make API call
            response = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=False
                ),
                timeout=self.timeout_sec
            )

            # Extract response
            content = response.choices[0].message.content
            first_token_time = time.time()

            # Extract token usage
            if response.usage:
                token_usage = TokenUsage(
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    total_tokens=response.usage.total_tokens
                )

            # Build metrics
            ttft_ms = int((first_token_time - start_time) * 1000)
            total_latency_ms = int((time.time() - start_time) * 1000)

            metrics = GenerationMetrics(
                ttft_ms=ttft_ms,
                total_latency_ms=total_latency_ms,
                token_usage=token_usage,
                model=model,
                success=True
            )

            return content, metrics

        except asyncio.TimeoutError:
            metrics = GenerationMetrics(
                ttft_ms=0,
                total_latency_ms=int((time.time() - start_time) * 1000),
                token_usage=token_usage,
                model=model,
                success=False,
                error_message="Request timeout"
            )
            return "", metrics

        except Exception as e:
            metrics = GenerationMetrics(
                ttft_ms=0,
                total_latency_ms=int((time.time() - start_time) * 1000),
                token_usage=token_usage,
                model=model,
                success=False,
                error_message=str(e)
            )
            return "", metrics

    def estimate_cost(self, token_usage: TokenUsage) -> float:
        """Estimate cost based on token usage"""
        try:
            # Load pricing data
            with open("pricing.json", "r") as f:
                pricing = json.load(f)

            model_pricing = pricing.get(self.model_name, {})
            input_rate = model_pricing.get("input_per_1m", 0.15)
            output_rate = model_pricing.get("output_per_1m", 0.60)

            # Calculate cost
            input_cost = (token_usage.prompt_tokens / 1_000_000) * input_rate
            output_cost = (token_usage.completion_tokens / 1_000_000) * output_rate

            return input_cost + output_cost

        except Exception as e:
            print(f"Error estimating cost: {e}")
            return 0.0

    async def health_check(self) -> Dict[str, Any]:
        """Check OpenAI API health"""
        try:
            start_time = time.time()

            response = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[{"role": "user", "content": "Hello"}],
                    max_tokens=5
                ),
                timeout=10
            )

            latency_ms = int((time.time() - start_time) * 1000)

            return {
                "status": "healthy",
                "model": self.model_name,
                "latency_ms": latency_ms,
                "response_length": len(response.choices[0].message.content)
            }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "model": self.model_name
            }

# Global client instance
openai_client = OpenAIClient()
