# API エンドポイント ガイド

WordPress RAG ChatbotのAPIエンドポイントの詳細な使用方法を説明します。

## 📋 目次

- [サーバー起動](#サーバー起動)
- [検索・質問エンドポイント](#検索質問エンドポイント)
- [RAG生成エンドポイント](#rag生成エンドポイント)
- [監視・管理エンドポイント](#監視管理エンドポイント)
- [レスポンス形式](#レスポンス形式)
- [エラーハンドリング](#エラーハンドリング)

## 🚀 サーバー起動

### 開発モード
```bash
uvicorn wp_chat.api.chat_api:app --reload --port 8080
```

### 本番モード
```bash
uvicorn wp_chat.api.chat_api:app --host 0.0.0.0 --port 8080
```

### カスタム設定
```bash
uvicorn wp_chat.api.chat_api:app --reload --port 8080 --workers 4
```

## 🔍 検索・質問エンドポイント

### POST /search
従来の検索機能（MVP1-3）

**リクエスト:**
```bash
curl -X POST http://localhost:8080/search \
  -H 'Content-Type: application/json' \
  -d '{
    "query": "VBA 文字列処理",
    "topk": 5,
    "mode": "hybrid",
    "rerank": true
  }'
```

**レスポンス:**
```json
{
  "results": [
    {
      "title": "VBAで文字列から拡張子を取得する方法",
      "url": "https://tsukiusagi.biz/vba-get-extension/",
      "snippet": "VBAでファイルパスから拡張子だけを抜き出す方法を解説します...",
      "score": 0.95,
      "post_id": "3922",
      "chunk_id": "3"
    }
  ],
  "metadata": {
    "total_results": 5,
    "search_time_ms": 45,
    "mode": "hybrid",
    "rerank_enabled": true
  }
}
```

### POST /ask
質問応答機能（MVP1-3）

**リクエスト:**
```bash
curl -X POST http://localhost:8080/ask \
  -H 'Content-Type: application/json' \
  -d '{
    "question": "プライバシーポリシーはどこにありますか？",
    "topk": 5,
    "mode": "hybrid",
    "rerank": true
  }'
```

**レスポンス:**
```json
{
  "answer": "プライバシーポリシーは以下のページで確認できます...",
  "sources": [
    {
      "title": "プライバシーポリシー",
      "url": "https://tsukiusagi.biz/privacy/",
      "snippet": "当サイトのプライバシーポリシーについて..."
    }
  ],
  "metadata": {
    "search_time_ms": 52,
    "answer_time_ms": 120,
    "total_time_ms": 172
  }
}
```

## 🤖 RAG生成エンドポイント（MVP4）

### POST /generate
OpenAI GPT-4o miniを使用したRAG生成

#### 非ストリーミング生成

**リクエスト:**
```bash
curl -X POST http://localhost:8080/generate \
  -H 'Content-Type: application/json' \
  -d '{
    "question": "VBAで文字列の処理方法を教えて",
    "topk": 5,
    "stream": false,
    "mode": "hybrid",
    "rerank": true,
    "user_id": "user123"
  }'
```

**レスポンス:**
```json
{
  "answer": "VBAで文字列を処理する方法について説明します[[1]]。\n\n主な方法として、InStrRev関数を使用して文字列の最後からドット（.）を探し、その位置から右側の文字列を抽出する方法があります[[2]]。\n\nまた、Mid関数やLeft関数、Right関数なども文字列操作に便利です[[1]]。",
  "references": [
    {
      "id": 1,
      "title": "VBAで文字列から拡張子を取得して、文字列として返す｜InStrRev",
      "url": "https://tsukiusagi.biz/vba-get-extension/"
    },
    {
      "id": 2,
      "title": "VBA文字列処理の基本",
      "url": "https://tsukiusagi.biz/vba-string-basics/"
    }
  ],
  "metadata": {
    "generation_time_ms": 2156,
    "ttft_ms": 1203,
    "total_tokens": 156,
    "model": "gpt-4o-mini",
    "citation_count": 2,
    "has_citations": true,
    "valid_citations": true
  }
}
```

#### ストリーミング生成

**リクエスト:**
```bash
curl -X POST http://localhost:8080/generate \
  -H 'Content-Type: application/json' \
  -d '{
    "question": "VBAで文字列の処理方法を教えて",
    "topk": 5,
    "stream": true,
    "mode": "hybrid",
    "rerank": true,
    "user_id": "user123"
  }'
```

**レスポンス（Server-Sent Events）:**
```
data: {"type": "metrics", "ttft_ms": 1203, "model": "gpt-4o-mini"}

data: {"type": "delta", "content": "VBAで文字列を処理する方法について説明します"}

data: {"type": "delta", "content": "[[1]]。"}

data: {"type": "delta", "content": "\n\n主な方法として、"}

...

data: {"type": "done", "metrics": {"generation_time_ms": 2156, "total_tokens": 156, "success": true}}

data: {"type": "references", "references": [{"id": 1, "title": "...", "url": "..."}]}
```

## 📊 監視・管理エンドポイント

### GET /stats/health
ヘルスチェック

**リクエスト:**
```bash
curl http://localhost:8080/stats/health
```

**レスポンス:**
```json
{
  "status": "healthy",
  "timestamp": "2024-10-24T14:30:00Z",
  "uptime_seconds": 3600,
  "version": "MVP4",
  "components": {
    "database": "healthy",
    "openai_api": "healthy",
    "search_index": "healthy"
  }
}
```

### GET /stats/slo
SLO（Service Level Objective）メトリクス

**リクエスト:**
```bash
curl http://localhost:8080/stats/slo
```

**レスポンス:**
```json
{
  "endpoints": {
    "search": {
      "avg_latency_ms": 45.2,
      "p95_latency_ms": 89.1,
      "success_rate": 0.998,
      "requests_per_minute": 12.5
    },
    "generate": {
      "avg_latency_ms": 2156.3,
      "p95_latency_ms": 4200.1,
      "avg_ttft_ms": 1203.5,
      "success_rate": 0.985,
      "avg_token_count": 156.2,
      "citation_rate": 0.92,
      "requests_per_minute": 3.2
    }
  },
  "window_minutes": 5,
  "last_updated": "2024-10-24T14:30:00Z"
}
```

### GET /stats/metrics
詳細メトリクス

**リクエスト:**
```bash
curl http://localhost:8080/stats/metrics
```

**レスポンス:**
```json
{
  "performance": {
    "avg_response_time_ms": 1250.5,
    "total_requests": 1250,
    "error_rate": 0.012
  },
  "generation": {
    "total_generations": 125,
    "avg_tokens_per_response": 156.2,
    "citation_rate": 0.92,
    "fallback_rate": 0.08
  },
  "cache": {
    "hit_rate": 0.35,
    "total_cached_items": 1250
  }
}
```

### GET /dashboard
監視ダッシュボード（HTML）

**リクエスト:**
```bash
curl http://localhost:8080/dashboard
```

**レスポンス:** HTMLダッシュボードページ

## 🔧 管理エンドポイント

### POST /admin/canary/rollout
カナリーロールアウト設定

**リクエスト:**
```bash
curl -X POST http://localhost:8080/admin/canary/rollout \
  -H 'Content-Type: application/json' \
  -d '{
    "percentage": 25,
    "feature": "generation"
  }'
```

**レスポンス:**
```json
{
  "status": "success",
  "message": "Canary rollout updated to 25%",
  "current_percentage": 25,
  "feature": "generation"
}
```

### GET /admin/canary/status
カナリー状態確認

**リクエスト:**
```bash
curl http://localhost:8080/admin/canary/status
```

**レスポンス:**
```json
{
  "enabled": true,
  "percentage": 25,
  "feature": "generation",
  "total_users": 1000,
  "canary_users": 250,
  "last_updated": "2024-10-24T14:30:00Z"
}
```

### POST /admin/backup/create
バックアップ作成

**リクエスト:**
```bash
curl -X POST http://localhost:8080/admin/backup/create \
  -H 'Content-Type: application/json' \
  -d '{
    "description": "Daily backup",
    "include_data": true,
    "include_index": true
  }'
```

**レスポンス:**
```json
{
  "backup_id": "backup_20241024_143000",
  "status": "created",
  "size_mb": 125.5,
  "created_at": "2024-10-24T14:30:00Z"
}
```

## 📝 レスポンス形式

### 共通メタデータ
```json
{
  "metadata": {
    "request_id": "req_123456789",
    "timestamp": "2024-10-24T14:30:00Z",
    "version": "MVP4",
    "processing_time_ms": 1250
  }
}
```

### エラーレスポンス
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request parameters",
    "details": {
      "field": "topk",
      "issue": "Value must be between 1 and 10"
    }
  },
  "request_id": "req_123456789",
  "timestamp": "2024-10-24T14:30:00Z"
}
```

## 🚨 エラーハンドリング

### HTTPステータスコード

| コード | 説明 | 例 |
|--------|------|-----|
| 200 | 成功 | 正常なレスポンス |
| 400 | バリデーションエラー | 不正なパラメータ |
| 401 | 認証エラー | APIキー無効 |
| 429 | レート制限 | リクエスト数超過 |
| 500 | サーバーエラー | 内部エラー |
| 503 | サービス利用不可 | メンテナンス中 |

### エラーコード一覧

| コード | 説明 | 解決方法 |
|--------|------|----------|
| `VALIDATION_ERROR` | パラメータ不正 | リクエスト形式を確認 |
| `RATE_LIMIT_EXCEEDED` | レート制限超過 | しばらく待ってから再試行 |
| `OPENAI_API_ERROR` | OpenAI API エラー | APIキーとクォータを確認 |
| `INDEX_NOT_FOUND` | インデックス未構築 | `python -m wp_chat.data.build_index` を実行 |
| `GENERATION_FAILED` | 生成失敗 | ログを確認して再試行 |

## 🔒 セキュリティ

### レート制限
- **デフォルト**: 60 requests/minute
- **生成エンドポイント**: 10 requests/minute
- **管理エンドポイント**: 5 requests/minute

### CORS設定
```json
{
  "allowed_origins": ["http://localhost:3000", "https://yourdomain.com"],
  "allowed_methods": ["GET", "POST"],
  "allowed_headers": ["Content-Type", "Authorization"]
}
```

## 📈 パフォーマンス最適化

### 推奨設定

#### 開発環境
```bash
# 軽量設定
curl -X POST http://localhost:8080/generate \
  -H 'Content-Type: application/json' \
  -d '{
    "question": "質問",
    "topk": 3,
    "mode": "dense",
    "stream": false
  }'
```

#### 本番環境
```bash
# 高品質設定
curl -X POST http://localhost:8080/generate \
  -H 'Content-Type: application/json' \
  -d '{
    "question": "質問",
    "topk": 8,
    "mode": "hybrid",
    "rerank": true,
    "stream": true
  }'
```

### キャッシュ戦略
- **検索結果**: 5分間キャッシュ
- **生成結果**: 1時間キャッシュ（同一質問）
- **インデックス**: メモリキャッシュ

## 🧪 テスト例

### 基本的なテスト
```bash
#!/bin/bash
# api_test.sh

BASE_URL="http://localhost:8080"

# ヘルスチェック
echo "Testing health endpoint..."
curl -s "$BASE_URL/stats/health" | jq

# 検索テスト
echo "Testing search endpoint..."
curl -s -X POST "$BASE_URL/search" \
  -H 'Content-Type: application/json' \
  -d '{"query": "test", "topk": 3}' | jq

# 生成テスト
echo "Testing generation endpoint..."
curl -s -X POST "$BASE_URL/generate" \
  -H 'Content-Type: application/json' \
  -d '{"question": "test question", "stream": false}' | jq
```

### パフォーマンステスト
```bash
#!/bin/bash
# performance_test.sh

BASE_URL="http://localhost:8080"

# 並列リクエストテスト
for i in {1..10}; do
  curl -s -X POST "$BASE_URL/generate" \
    -H 'Content-Type: application/json' \
    -d "{\"question\": \"test question $i\", \"stream\": false}" &
done

wait
echo "Performance test completed"
```

---

**API documentation complete! 🚀**
