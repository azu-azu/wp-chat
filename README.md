# WordPress RAG Chatbot (MVP4)

Advanced RAG (Retrieval-Augmented Generation) chatbot for WordPress sites with OpenAI integration, streaming responses, and citation tracking.

## 🚀 Features

- **RAG Generation**: OpenAI GPT-4o mini integration with citation tracking
- **Streaming Responses**: Real-time token delivery for better UX
- **Hybrid Search**: Dense + BM25 + Cross-encoder reranking
- **Citation Tracking**: Source attribution with `[[1]]` references
- **SLO Monitoring**: Performance metrics and alerting
- **Canary Deployment**: Gradual feature rollout
- **CLI Tools**: Interactive testing and management

## 🏗️ Architecture

```
wp_chat/                    # Main application package
├── api/                    # FastAPI endpoints
│   ├── chat_api.py        # Main API server
│   └── models.py          # Request/response models
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
WP_BASE_URL=https://your-blog.example.com
OPENAI_API_KEY=sk-proj-your-openai-api-key-here
```

### 3. Data Pipeline
```bash
# Fetch WordPress content
python -m wp_chat.data.fetch_wp

# Clean and process text
python -m wp_chat.data.clean_text

# Build search index
python -m wp_chat.data.build_index
```

## 🚀 Running the Application

### API Server
```bash
# Development mode
uvicorn wp_chat.api.chat_api:app --reload --port 8080

# Production mode
uvicorn wp_chat.api.chat_api:app --host 0.0.0.0 --port 8080
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

### Quick Test
```bash
# Test all major components
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
   uvicorn wp_chat.api.chat_api:app --reload --port 8080
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
3. Add tests
4. Update documentation
5. Submit PR

### Code Style
- Follow PEP 8
- Use type hints
- Add docstrings
- Write tests

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

## 📋 Planning Documents

- **[🔧 改善実装計画 (2025-11-01)](plans/2025-11-01-improvement-plan.md)** - 安定運用に向けたTOP8改善項目

## 📞 Support

For issues and questions:
- Create GitHub issue
- Check troubleshooting section
- Review logs for errors
- Consult documentation guides above
