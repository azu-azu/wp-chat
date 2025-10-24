#!/usr/bin/env python3
# test_mvp4.py - Quick test of MVP4 RAG generation
import os
import sys
import asyncio

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_imports():
    """Test that all modules can be imported"""
    print("🧪 Testing imports...")

    try:
        from src.generation import generation_pipeline
        print("✅ generation.py imported")

        from src.prompts import build_messages, validate_citations
        print("✅ prompts.py imported")

        from src.openai_client import openai_client
        print("✅ openai_client.py imported")

        from src.config import get_config_value
        print("✅ config.py imported")

        return True
    except Exception as e:
        print(f"❌ Import error: {e}")
        return False

def test_config():
    """Test configuration loading"""
    print("\n🔧 Testing configuration...")

    try:
        from src.config import get_config_value

        # Test LLM config
        provider = get_config_value("llm.provider")
        alias = get_config_value("llm.alias")
        model_name = get_config_value(f"models.{alias}.name")

        print(f"✅ Provider: {provider}")
        print(f"✅ Alias: {alias}")
        print(f"✅ Model: {model_name}")

        # Test generation config
        context_max = get_config_value("generation.context_max_tokens")
        citation_style = get_config_value("generation.citation_style")

        print(f"✅ Context max tokens: {context_max}")
        print(f"✅ Citation style: {citation_style}")

        return True
    except Exception as e:
        print(f"❌ Config error: {e}")
        return False

def test_prompt_building():
    """Test prompt building"""
    print("\n💬 Testing prompt building...")

    try:
        from src.prompts import build_messages, validate_citations

        # Mock documents
        docs = [
            {
                "title": "Test Document 1",
                "url": "https://example.com/doc1",
                "snippet": "This is a test document with relevant information."
            },
            {
                "title": "Test Document 2",
                "url": "https://example.com/doc2",
                "snippet": "Another test document with additional context."
            }
        ]

        # Build messages
        messages = build_messages("What is the main topic?", docs)

        print(f"✅ Messages built: {len(messages)} messages")
        print(f"✅ System prompt length: {len(messages[0]['content'])} chars")
        print(f"✅ User prompt length: {len(messages[1]['content'])} chars")

        # Test citation validation
        test_text = "This is a test with citations [[1]] and [[2]]."
        validation = validate_citations(test_text, len(docs))

        print(f"✅ Citations found: {validation['citations']}")
        print(f"✅ Citation count: {validation['citation_count']}")
        print(f"✅ Is valid: {validation['is_valid']}")

        return True
    except Exception as e:
        print(f"❌ Prompt building error: {e}")
        return False

def test_context_composition():
    """Test context composition"""
    print("\n📝 Testing context composition...")

    try:
        from src.generation import generation_pipeline

        # Mock documents
        docs = [
            {
                "title": "Document 1",
                "url": "https://example.com/doc1",
                "snippet": "This is a long document with lots of content that should be truncated if it exceeds the token limit.",
                "post_id": "1",
                "chunk_id": "1",
                "hybrid_score": 0.95
            },
            {
                "title": "Document 2",
                "url": "https://example.com/doc2",
                "snippet": "Another document with different content.",
                "post_id": "2",
                "chunk_id": "1",
                "hybrid_score": 0.87
            }
        ]

        # Process context
        processed_docs, metadata = generation_pipeline.process_retrieval_results(docs)

        print(f"✅ Processed docs: {len(processed_docs)}")
        print(f"✅ Total tokens: {metadata['total_tokens']}")
        print(f"✅ Chunks used: {metadata['chunks_used']}")
        print(f"✅ Original chunks: {metadata['original_chunks']}")

        return True
    except Exception as e:
        print(f"❌ Context composition error: {e}")
        return False

def test_openai_client_init():
    """Test OpenAI client initialization"""
    print("\n🤖 Testing OpenAI client...")

    try:
        from src.openai_client import openai_client

        # Test model info
        model_info = openai_client.get_model_info()

        print(f"✅ Model alias: {model_info['alias']}")
        print(f"✅ Model name: {model_info['name']}")
        print(f"✅ Temperature: {model_info['temperature']}")
        print(f"✅ Max tokens: {model_info['max_tokens']}")

        # Test if API key is set
        api_key = os.getenv('OPENAI_API_KEY')
        if api_key:
            print(f"✅ API key is set (length: {len(api_key)})")
        else:
            print("⚠️  API key not set - set OPENAI_API_KEY environment variable")

        return True
    except Exception as e:
        print(f"❌ OpenAI client error: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 MVP4 RAG Generation - Quick Test")
    print("=" * 50)

    tests = [
        test_imports,
        test_config,
        test_prompt_building,
        test_context_composition,
        test_openai_client_init
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1
        print()

    print("=" * 50)
    print(f"📊 Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! MVP4 implementation looks good.")
        print("\n📋 Next steps:")
        print("1. Set OPENAI_API_KEY environment variable")
        print("2. Run: python src/generate_cli.py --health")
        print("3. Test with: python src/generate_cli.py --interactive")
        return 0
    else:
        print("❌ Some tests failed. Check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
