#!/usr/bin/env python3
# src/generate_cli.py - CLI tool for testing RAG generation
import asyncio
import json
import sys
import argparse
from typing import Optional
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ..generation.generation import generation_pipeline
from ..generation.openai_client import openai_client
from ..core.config import get_config_value

async def test_generation(question: str, topk: int = 5, stream: bool = True, mode: str = "hybrid", rerank: bool = False):
    """Test generation with a question"""
    print(f"🔍 Testing generation for: '{question}'")
    print(f"📊 Parameters: topk={topk}, stream={stream}, mode={mode}, rerank={rerank}")
    print("-" * 60)

    try:
        # Mock retrieval results (in real usage, this would come from hybrid search)
        mock_docs = [
            {
                "title": "Sample Document 1",
                "url": "https://example.com/doc1",
                "snippet": "This is a sample document about the topic you asked about. It contains relevant information that should help answer your question.",
                "post_id": "1",
                "chunk_id": "1",
                "hybrid_score": 0.95,
                "ce_score": 0.88
            },
            {
                "title": "Sample Document 2",
                "url": "https://example.com/doc2",
                "snippet": "Another relevant document with additional context and details about the subject matter.",
                "post_id": "2",
                "chunk_id": "1",
                "hybrid_score": 0.87,
                "ce_score": 0.82
            }
        ]

        # Process context
        processed_docs, context_metadata = generation_pipeline.process_retrieval_results(mock_docs)
        print(f"📝 Context processed: {context_metadata['chunks_used']} chunks, {context_metadata['total_tokens']} tokens")

        # Build prompt
        messages, prompt_stats = generation_pipeline.build_prompt(question, processed_docs)
        print(f"💬 Prompt built: {prompt_stats['estimated_tokens']} tokens")

        if stream:
            print("\n🌊 Streaming response:")
            print("-" * 40)

            full_response = ""
            async for chunk in openai_client.stream_chat(messages):
                if chunk["type"] == "delta":
                    content = chunk["content"]
                    full_response += content
                    print(content, end="", flush=True)

                elif chunk["type"] == "metrics":
                    print(f"\n⚡ TTFT: {chunk['ttft_ms']}ms, Model: {chunk['model']}")

                elif chunk["type"] == "done":
                    metrics = chunk["metrics"]
                    print(f"\n\n📊 Final metrics:")
                    print(f"   Total latency: {metrics['total_latency_ms']}ms")
                    print(f"   Tokens: {metrics['token_usage']['total_tokens']}")
                    print(f"   Success: {metrics['success']}")

                    # Post-process response
                    result = generation_pipeline.post_process_response(full_response, processed_docs)

                    print(f"\n📚 References:")
                    for ref in result.references:
                        print(f"   [{ref['id']}] {ref['title']}")
                        print(f"        {ref['url']}")

                    print(f"\n✅ Citations found: {result.metadata['citation_count']}")
                    print(f"✅ Response valid: {result.is_valid}")

                elif chunk["type"] == "error":
                    print(f"\n❌ Error: {chunk['error']}")
                    result = generation_pipeline.generate_fallback_response(question, processed_docs)
                    print(f"🔄 Fallback response: {result.answer}")

        else:
            print("\n📝 Non-streaming response:")
            print("-" * 40)

            content, metrics = await openai_client.chat_completion(messages)

            if metrics.success:
                print(content)
                print(f"\n📊 Metrics:")
                print(f"   TTFT: {metrics.ttft_ms}ms")
                print(f"   Total latency: {metrics.total_latency_ms}ms")
                print(f"   Tokens: {metrics.token_usage.total_tokens}")

                # Post-process response
                result = generation_pipeline.post_process_response(content, processed_docs)

                print(f"\n📚 References:")
                for ref in result.references:
                    print(f"   [{ref['id']}] {ref['title']}")
                    print(f"        {ref['url']}")

                print(f"\n✅ Citations found: {result.metadata['citation_count']}")
                print(f"✅ Response valid: {result.is_valid}")
            else:
                print(f"❌ Generation failed: {metrics.error_message}")
                result = generation_pipeline.generate_fallback_response(question, processed_docs)
                print(f"🔄 Fallback response: {result.answer}")

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

    return True

async def health_check():
    """Check OpenAI API health"""
    print("🏥 Checking OpenAI API health...")

    try:
        health = await openai_client.health_check()
        print(f"Status: {health['status']}")

        if health['status'] == 'healthy':
            print(f"✅ Model: {health['model']}")
            print(f"✅ Latency: {health['latency_ms']}ms")
        else:
            print(f"❌ Error: {health['error']}")

        return health['status'] == 'healthy'

    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Test RAG generation")
    parser.add_argument("question", nargs="?", help="Question to ask")
    parser.add_argument("--topk", type=int, default=5, help="Number of documents to retrieve")
    parser.add_argument("--no-stream", action="store_true", help="Disable streaming")
    parser.add_argument("--mode", choices=["dense", "bm25", "hybrid"], default="hybrid", help="Search mode")
    parser.add_argument("--rerank", action="store_true", help="Enable reranking")
    parser.add_argument("--health", action="store_true", help="Check API health")
    parser.add_argument("--interactive", action="store_true", help="Interactive mode")

    args = parser.parse_args()

    # Check if OpenAI API key is set
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ OPENAI_API_KEY environment variable is required")
        print("   Set it with: export OPENAI_API_KEY='your-key-here'")
        return 1

    async def run():
        if args.health:
            success = await health_check()
            return 0 if success else 1

        if args.interactive:
            print("🎯 Interactive RAG Generation Test")
            print("Type 'quit' to exit, 'health' to check API status")
            print("-" * 50)

            while True:
                try:
                    question = input("\n❓ Question: ").strip()

                    if question.lower() in ['quit', 'exit', 'q']:
                        break

                    if question.lower() == 'health':
                        await health_check()
                        continue

                    if not question:
                        continue

                    await test_generation(
                        question,
                        topk=args.topk,
                        stream=not args.no_stream,
                        mode=args.mode,
                        rerank=args.rerank
                    )

                except KeyboardInterrupt:
                    print("\n👋 Goodbye!")
                    break
                except Exception as e:
                    print(f"❌ Error: {e}")

            return 0

        if not args.question:
            print("❌ Please provide a question or use --interactive mode")
            return 1

        success = await test_generation(
            args.question,
            topk=args.topk,
            stream=not args.no_stream,
            mode=args.mode,
            rerank=args.rerank
        )

        return 0 if success else 1

    return asyncio.run(run())

if __name__ == "__main__":
    sys.exit(main())
