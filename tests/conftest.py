# tests/conftest.py - pytest共通設定・フィクスチャ
import os
import sys
from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock, Mock

import pytest
from fastapi.testclient import TestClient

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


# ========================================
# テスト用設定オーバーライド
# ========================================


@pytest.fixture(scope="session")
def test_config() -> dict[str, Any]:
    """テスト用設定"""
    return {
        "llm": {"provider": "openai", "alias": "default-mini", "timeout_sec": 30, "stream": True},
        "generation": {
            "context_max_tokens": 3500,
            "chunk_max_tokens": 1000,
            "max_chunks": 5,
            "citation_style": "bracketed",
        },
        "api": {
            "cache": {
                "enabled": True,
                "search_ttl": 1800,
                "embedding_ttl": 7200,
                "max_size_mb": 100,
            },
            "rate_limit": {
                "enabled": False,  # テスト時は無効化
                "max_requests": 100,
                "window_seconds": 3600,
            },
        },
    }


# ========================================
# モックOpenAIクライアント
# ========================================


@pytest.fixture
def mock_openai_client():
    """モックOpenAIクライアント"""
    mock_client = MagicMock()

    # 非ストリーミングレスポンス
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = "これはテスト回答です。[[1]]"
    mock_response.usage.total_tokens = 100
    mock_response.model = "gpt-4o-mini"

    mock_client.chat.completions.create.return_value = mock_response

    return mock_client


@pytest.fixture
def mock_openai_streaming_client():
    """モックOpenAIストリーミングクライアント"""
    mock_client = MagicMock()

    # ストリーミングレスポンス
    def mock_stream():
        chunks = [
            Mock(choices=[Mock(delta=Mock(content="これは"))]),
            Mock(choices=[Mock(delta=Mock(content="テスト"))]),
            Mock(choices=[Mock(delta=Mock(content="回答です。"))]),
            Mock(choices=[Mock(delta=Mock(content="[[1]]"))]),
        ]
        for chunk in chunks:
            yield chunk

    mock_client.chat.completions.create.return_value = mock_stream()

    return mock_client


# ========================================
# テスト用データ
# ========================================


@pytest.fixture
def sample_search_results() -> list:
    """サンプル検索結果"""
    return [
        {
            "id": 1,
            "title": "VBA 文字列処理の基本",
            "url": "https://example.com/vba-string-basics",
            "snippet": "VBAで文字列を処理する方法について...",
            "hybrid_score": 0.95,
            "dense_score": 0.9,
            "bm25_score": 0.8,
        },
        {
            "id": 2,
            "title": "VBA 配列操作",
            "url": "https://example.com/vba-arrays",
            "snippet": "VBAでの配列の使い方...",
            "hybrid_score": 0.85,
            "dense_score": 0.8,
            "bm25_score": 0.7,
        },
        {
            "id": 3,
            "title": "VBA エラーハンドリング",
            "url": "https://example.com/vba-error-handling",
            "snippet": "VBAのエラー処理について...",
            "hybrid_score": 0.75,
            "dense_score": 0.7,
            "bm25_score": 0.6,
        },
    ]


@pytest.fixture
def sample_documents() -> list:
    """サンプルドキュメント"""
    return [
        {
            "id": 1,
            "title": "VBA 文字列処理の基本",
            "url": "https://example.com/vba-string-basics",
            "content": "VBAで文字列を処理する基本的な方法について説明します。Left関数、Right関数、Mid関数などを使用します。",
            "category": "VBA",
        },
        {
            "id": 2,
            "title": "VBA 配列操作",
            "url": "https://example.com/vba-arrays",
            "content": "VBAでの配列の使い方。動的配列、多次元配列などについて解説します。",
            "category": "VBA",
        },
    ]


# ========================================
# テスト用FAISSインデックス（モック）
# ========================================


@pytest.fixture
def mock_faiss_index():
    """モックFAISSインデックス"""
    mock_index = MagicMock()

    # search メソッドのモック
    mock_index.search.return_value = (
        [[0.1, 0.2, 0.3]],  # distances
        [[0, 1, 2]],  # indices
    )

    mock_index.ntotal = 100  # インデックス内のベクトル数

    return mock_index


# ========================================
# FastAPI TestClient
# ========================================


@pytest.fixture
def test_client() -> Generator[TestClient, None, None]:
    """FastAPI TestClient"""
    from src.api.chat_api import app

    # テスト用環境変数設定
    os.environ["OPENAI_API_KEY"] = "sk-test-key"
    os.environ["API_KEY_REQUIRED"] = "false"
    os.environ["RATE_LIMIT_ENABLED"] = "false"

    with TestClient(app) as client:
        yield client


# ========================================
# テスト用キャッシュディレクトリ
# ========================================


@pytest.fixture
def temp_cache_dir(tmp_path):
    """一時キャッシュディレクトリ"""
    cache_dir = tmp_path / "test_cache"
    cache_dir.mkdir()
    return str(cache_dir)


# ========================================
# クリーンアップ
# ========================================


@pytest.fixture(autouse=True)
def cleanup_test_files():
    """テスト実行後のクリーンアップ"""
    yield
    # テスト後の処理（必要に応じて）
    pass


# ========================================
# pytest設定
# ========================================


def pytest_configure(config):
    """pytest設定"""
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "e2e: mark test as an end-to-end test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
