# WordPress RAG Chatbot (MVP4)

Advanced RAG (Retrieval-Augmented Generation) chatbot for WordPress sites with OpenAI integration, streaming responses, and citation tracking.

## ⚡️ Quick Start (5 minutes)

```bash
# 1. Clone and setup
git clone <repo-url> wp-chat
cd wp-chat
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Edit .env: Add your WP_BASE_URL and OPENAI_API_KEY

# 3. Build index
python -m wp_chat.data.fetch_wp       # Fetch WordPress posts
python -m wp_chat.data.clean_text     # Clean and chunk text
python -m wp_chat.data.build_index    # Build FAISS index
python -m wp_chat.data.build_bm25     # Build BM25 index

# 4. Start server
uvicorn wp_chat.api.main:app --reload --port 8080

# 5. Test
python -m wp_chat.cli.generate_cli --interactive
```

## 🚀 Features

- **RAG Generation**: OpenAI GPT-4o mini integration with citation tracking
- **Streaming Responses**: Real-time token delivery for better UX
- **Hybrid Search**: Dense + BM25 + Cross-encoder reranking
- **Citation Tracking**: Source attribution with `[[1]]` references
- **SLO Monitoring**: Performance metrics and alerting
- **Canary Deployment**: Gradual feature rollout
- **CLI Tools**: Interactive testing and management
- **Comprehensive Testing**: 251 unit tests with 93% coverage (Clean Architecture)

## 🏗️ Architecture

```
wp_chat/                    # Main application package
├── api/                    # Presentation Layer - FastAPI endpoints
│   ├── main.py            # Main FastAPI app (entry point)
│   ├── models.py          # Pydantic request/response models
│   └── routers/           # Modular endpoint routers
│       ├── chat.py        # /search, /ask, /generate
│       ├── stats.py       # /stats/* (monitoring)
│       ├── admin_canary.py    # /admin/canary/*
│       ├── admin_incidents.py # /admin/incidents/*
│       ├── admin_backup.py    # /admin/backup/*
│       └── admin_cache.py     # /admin/cache/*
├── services/               # Application Layer - Business logic
│   ├── search_service.py  # Search operations
│   ├── generation_service.py  # RAG generation
│   └── cache_service.py   # Cache management
├── domain/                 # Domain Layer - Business models (Phase 3)
│   ├── models/            # Domain entities
│   │   ├── document.py    # Document model
│   │   ├── search_result.py   # Search result model
│   │   └── generation_result.py # Generation result model
│   ├── repositories/      # Repository interfaces
│   │   ├── search_repository.py   # Search repository interface
│   │   └── cache_repository.py    # Cache repository interface
│   └── value_objects/     # Value objects
│       ├── query.py       # Query value object
│       └── score.py       # Score value object
├── cli/                    # Command-line tools
│   ├── generate_cli.py    # RAG generation testing
│   ├── backup_cli.py      # Backup management
│   ├── canary_cli.py      # Canary deployment
│   └── incident_cli.py    # Incident management
├── core/                   # Core utilities
│   ├── config.py          # Configuration management
│   ├── cache.py           # Response caching
│   ├── rate_limit.py      # Rate limiting
│   ├── slo_monitoring.py  # Performance monitoring
│   ├── runbook.py         # Emergency procedures
│   ├── auth.py            # Authentication
│   ├── exceptions.py      # Custom exceptions
│   └── logging_config.py  # Logging setup
├── data/                   # Data processing
│   ├── fetch_wp.py        # WordPress API fetch
│   ├── clean_text.py      # Text cleaning
│   ├── build_index.py     # FAISS index building
│   ├── build_bm25.py      # BM25 index building
│   └── utils_chunk.py     # Text chunking
├── generation/             # RAG generation (MVP4)
│   ├── generation.py      # Generation pipeline
│   ├── openai_client.py   # OpenAI API client
│   ├── prompts.py         # Prompt engineering
│   └── highlight.py       # Result highlighting
├── management/             # Operations & monitoring
│   ├── ab_logging.py      # A/B test logging
│   ├── canary_manager.py  # Canary deployment
│   ├── dashboard.py       # Monitoring dashboard
│   ├── model_manager.py   # Model management
│   └── backup_manager.py  # Backup operations
└── retrieval/              # Search & scoring
    ├── search_hybrid.py   # Hybrid search
    ├── rerank.py          # Cross-encoder reranking
    ├── composite_scoring.py # Scoring strategies
    └── eval_retrieval.py  # Retrieval evaluation
```

## 📂 Project Structure

```
wp-chat/
├── wp_chat/            # Main application package (see above)
├── guide/              # 📚 User guides and documentation
├── plans/              # 📋 Implementation planning documents
├── tests/              # 🧪 Test suite (251 tests, 93% coverage)
│   ├── unit/          # Unit tests
│   │   ├── domain/    # Domain layer tests (163 tests, 100% coverage)
│   │   └── services/  # Service layer tests (88 tests, 94-100% coverage)
│   ├── integration/   # Integration tests
│   └── e2e/           # End-to-end tests
├── backups/            # 💾 Automatic backups
├── cache/              # 🚀 API response cache
├── logs/               # 📊 Application logs
├── data/               # 📁 Indexes and data files
│   ├── raw/           # Raw WordPress data
│   ├── processed/     # Cleaned and chunked data
│   └── index/         # Search indexes
│       ├── wp.faiss          # FAISS vector index
│       ├── wp.meta.json      # Document metadata
│       ├── wp.tfidf.pkl      # BM25 vectorizer
│       └── wp.tfidf.npz      # BM25 matrix
├── config.yml          # ⚙️ Application configuration
├── .env                # 🔐 Environment variables (create from .env.example)
├── requirements.txt    # 📦 Python dependencies
└── README.md           # 📖 This file
```

## 📋 Prerequisites

- Python 3.10+
- OpenAI API key
- macOS/Linux (tested on macOS)

## ⚙️ Setup

### 1. Environment Setup
```bash
# Create virtual environment
python -m venv .venv && source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration
Create `.env` file:
```bash
cp .env.example .env
# Edit .env with your settings
```

Required environment variables:
```bash
# .env

# Required
WP_BASE_URL=https://your-blog.example.com
OPENAI_API_KEY=sk-proj-your-openai-api-key-here

# Optional (for production)
API_KEY=your-admin-api-key-here              # For /admin/* endpoints
ALLOWED_ORIGINS=http://localhost:3000        # CORS origins (comma-separated)
PORT=8080                                     # API server port
LOG_LEVEL=INFO                                # DEBUG, INFO, WARNING, ERROR
```

### 3. Data Pipeline
```bash
# Step 1: Fetch WordPress content
python -m wp_chat.data.fetch_wp
# Creates: data/raw/wp_posts.jsonl

# Step 2: Clean and chunk text
python -m wp_chat.data.clean_text
# Creates: data/processed/wp_cleaned.jsonl, wp_chunks.jsonl

# Step 3: Build FAISS index (dense/semantic search)
python -m wp_chat.data.build_index
# Creates: data/index/wp.faiss, wp.meta.json

# Step 4: Build BM25 index (keyword search)
python -m wp_chat.data.build_bm25
# Creates: data/index/wp.tfidf.pkl, wp.tfidf.npz

# Verify all indexes are created
ls -lh data/index/
# Expected: wp.faiss, wp.meta.json, wp.tfidf.pkl, wp.tfidf.npz
```

## 🚀 Running the Application

### API Server
```bash
# Development mode
uvicorn wp_chat.api.main:app --reload --port 8080

# Production mode
uvicorn wp_chat.api.main:app --host 0.0.0.0 --port 8080
```

### CLI Tools

#### RAG Generation Testing
```bash
# Health check
python -m wp_chat.cli.generate_cli --health

# Single question
python -m wp_chat.cli.generate_cli "Pythonプログラミングの基本を教えて"

# Interactive mode (recommended)
python -m wp_chat.cli.generate_cli --interactive

# With options
python -m wp_chat.cli.generate_cli "Webアプリケーションの作り方を教えて" --topk 5 --mode hybrid --rerank
```

#### Other CLI Tools
```bash
# Backup management
python -m wp_chat.cli.backup_cli --help

# Canary deployment
python -m wp_chat.cli.canary_cli --help

# Incident management
python -m wp_chat.cli.incident_cli --help
```

## 🎯 API Quick Reference

| Endpoint | Method | Purpose | Auth Required |
|----------|--------|---------|---------------|
| `/search` | POST | Hybrid search with rerank | Optional |
| `/ask` | POST | Search with highlighted snippets | Optional |
| `/generate` | POST | RAG generation (streaming) | Optional |
| `/stats/health` | GET | Health check | None |
| `/stats/slo` | GET | SLO metrics | None |
| `/stats/ab` | GET | A/B testing statistics | None |
| `/stats/cache` | GET | Cache statistics | None |
| `/dashboard` | GET | Monitoring dashboard UI | None |
| `/admin/canary/status` | GET | Canary deployment status | API Key |
| `/admin/canary/rollout` | POST | Update rollout percentage | API Key |
| `/admin/backup/list` | GET | List backups | API Key |
| `/admin/backup/create` | POST | Create backup | API Key |
| `/admin/incidents/status` | GET | Incident status | API Key |

**Note:** Admin endpoints (`/admin/*`) require API key authentication via `X-API-Key` header.

## 🔧 API Endpoints

### Search & Ask
```bash
# Traditional search
curl -X POST http://localhost:8080/search \
  -H 'Content-Type: application/json' \
  -d '{"query":"Python プログラミング","topk":5}'

# Ask with context
curl -X POST http://localhost:8080/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"プライバシーポリシーは？","topk":5}'
```

### RAG Generation (MVP4)
```bash
# Non-streaming generation
curl -X POST http://localhost:8080/generate \
  -H 'Content-Type: application/json' \
  -d '{"question":"Pythonプログラミングの基本を教えて","stream":false}'

# Streaming generation
curl -X POST http://localhost:8080/generate \
  -H 'Content-Type: application/json' \
  -d '{"question":"Pythonプログラミングの基本を教えて","stream":true}'
```

### Monitoring & Admin
```bash
# Health status
curl http://localhost:8080/stats/health

# SLO metrics
curl http://localhost:8080/stats/slo

# Dashboard
curl http://localhost:8080/dashboard

# Canary status
curl http://localhost:8080/admin/canary/status
```

## 📊 Configuration

### config.yml
```yaml
# LLM Configuration
llm:
  provider: openai
  alias: default-mini
  timeout_sec: 30
  stream: true

models:
  default-mini:
    name: gpt-4o-mini
    temperature: 0.2
    max_tokens: 700
    description: "Cost-efficient, fast, good Japanese support"

# Generation settings
generation:
  context_max_tokens: 3500
  chunk_max_tokens: 1000
  max_chunks: 5
  citation_style: "bracketed"

# SLO targets
api:
  slo:
    generate:
      ttft_ms: 1200         # Time to first token
      p95_latency_ms: 6000  # Target p95 latency
      success_rate: 0.98    # Target success rate
```

## 🧪 Testing

### Unit Tests (251 tests, 93% coverage ✅)

The project has comprehensive unit test coverage for Domain and Service layers following Clean Architecture principles.

#### Running Tests
```bash
# Run all unit tests
pytest tests/unit/ -v

# Run specific layer
pytest tests/unit/domain/ -v      # Domain layer (163 tests)
pytest tests/unit/services/ -v    # Service layer (88 tests)

# Run with coverage report
pytest tests/unit/domain/ tests/unit/services/ \
  --cov=wp_chat/domain \
  --cov=wp_chat/services \
  --cov-report=term-missing \
  --cov-report=html

# View HTML coverage report
open htmlcov/index.html
```

#### Test Coverage by Layer
| Layer | Coverage | Tests | Status |
|-------|----------|-------|--------|
| **Domain Models** | 100% | 108 | ✅ |
| **Value Objects** | 100% | 55 | ✅ |
| **Services** | 94-100% | 88 | ✅ |
| **Overall** | **93%** | **251** | ✅ |

#### Test Organization
```
tests/unit/
├── domain/                # Domain layer tests (163 tests)
│   ├── test_query.py     # Query value object (22 tests)
│   ├── test_score.py     # Score value object (33 tests)
│   ├── test_document.py  # Document model (23 tests)
│   ├── test_search_result.py    # SearchResult model (33 tests)
│   └── test_generation_result.py # GenerationResult model (52 tests)
└── services/              # Service layer tests (88 tests)
    ├── test_search_service.py      # SearchService (27 tests)
    ├── test_generation_service.py  # GenerationService (32 tests)
    └── test_cache_service.py       # CacheService (29 tests)
```

#### What's Tested
- ✅ **Domain Models**: Document, SearchResult, GenerationResult
- ✅ **Value Objects**: Query validation, Score calculations
- ✅ **Services**: Search, Generation, Cache operations
- ✅ **Edge Cases**: Unicode, empty values, boundary conditions
- ✅ **Business Logic**: Relevance scoring, snippet creation, cache key generation

### Integration Testing
```bash
# Quick integration test
python3 test_mvp4.py
```

### Interactive Testing
```bash
# Start interactive mode
python -m wp_chat.cli.generate_cli --interactive

# Example session:
# Q: Pythonプログラミングの基本を教えて
# A: [Streaming response with citations]
```

### API Testing
```bash
# Test search
curl -X POST http://localhost:8080/search \
  -H 'Content-Type: application/json' \
  -d '{"query":"test","topk":3}' | jq

# Test generation
curl -X POST http://localhost:8080/generate \
  -H 'Content-Type: application/json' \
  -d '{"question":"test question","stream":false}' | jq
```

## 📈 Monitoring

### SLO Metrics
- **TTFT**: Time to First Token ≤ 1.2s
- **P95 Latency**: ≤ 6s
- **Success Rate**: ≥ 98%
- **Citation Rate**: Track citation usage

### Dashboard
Access the monitoring dashboard at:
```
http://localhost:8080/dashboard
```

### Metrics Endpoints
```bash
# Performance metrics
curl http://localhost:8080/stats/metrics

# Cache statistics
curl http://localhost:8080/stats/cache

# Rate limit status
curl http://localhost:8080/stats/rate-limit
```

## 🔄 Deployment

### Canary Deployment
```bash
# Enable canary for 10% of users
curl -X POST http://localhost:8080/admin/canary/rollout \
  -H 'Content-Type: application/json' \
  -d '{"percentage": 10}'

# Check canary status
curl http://localhost:8080/admin/canary/status
```

### Backup & Recovery
```bash
# Create backup
python -m wp_chat.cli.backup_cli create

# List backups
python -m wp_chat.cli.backup_cli list

# Restore backup
python -m wp_chat.cli.backup_cli restore <backup_id>
```

## 🚨 Troubleshooting

### Common Issues

1. **Import Errors**
   ```bash
   # Ensure you're in the project root
   cd /path/to/wp-chat
   source .venv/bin/activate
   ```

2. **OpenAI API Errors**
   ```bash
   # Check API key
   python -m wp_chat.cli.generate_cli --health
   ```

3. **Index Not Found**
   ```bash
   # Rebuild index
   python -m wp_chat.data.build_index
   ```

4. **Port Conflicts**
   ```bash
   # Kill existing processes
   pkill -f uvicorn
   # Start fresh
   uvicorn wp_chat.api.main:app --reload --port 8080
   ```

### Logs
```bash
# Check application logs
tail -f logs/app.log

# Check error logs
tail -f logs/error.log
```

## 📚 Development

### Adding New Features
1. Create feature branch
2. Implement in appropriate module
3. **Add tests** (maintain 80%+ coverage)
4. Update documentation
5. Submit PR

### Code Style
- Follow PEP 8
- Use type hints
- Add docstrings
- Write tests for all new code

### Testing Guidelines
```bash
# Before committing, run tests
pytest tests/unit/ -v

# Check test coverage
pytest tests/unit/ --cov=wp_chat --cov-report=term-missing

# Ensure coverage stays above 80%
pytest tests/unit/domain/ tests/unit/services/ \
  --cov=wp_chat/domain \
  --cov=wp_chat/services \
  --cov-report=html

# Pre-commit hooks will check:
# - ruff (linting)
# - ruff-format (formatting)
# - mypy (type checking)
```

### Test-Driven Development (TDD)
1. **Write tests first** for new features
2. **Run tests** to see them fail
3. **Implement** the feature
4. **Run tests** to see them pass
5. **Refactor** while keeping tests green

### Test Structure
- **Domain Layer**: Test business logic in isolation
- **Service Layer**: Test with mocked dependencies
- **Integration**: Test component interactions
- **E2E**: Test full user workflows

## 📄 License

MIT License - see LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Add tests
5. Submit pull request

## 📚 Documentation

- **[📖 ドキュメントガイド](guide/readme.md)** - ドキュメントの概要と読み方
- **[🖥️ CLI実行ガイド](guide/cli_guide.md)** - CLIツールの詳細な使用方法
- **[🌐 APIエンドポイントガイド](guide/api_guide.md)** - APIの詳細な仕様と使用例
- **[💾 バックアップ・復元ガイド](guide/backup_guide.md)** - バックアップシステムの使用方法
- **[🚨 インシデント対応ガイド](guide/incident_runbook.md)** - 緊急対応手順
- **[🎯 MVP4実装サマリー](guide/mvp4_summary.md)** - RAG生成機能の実装内容
- **[⚙️ 設定ファイル](config.yml)** - アプリケーション設定
- **[💰 価格設定](pricing.json)** - LLMモデルの価格情報


## 📞 Support

For issues and questions:
- Create GitHub issue
- Check troubleshooting section
- Review logs for errors
- Consult documentation guides above
