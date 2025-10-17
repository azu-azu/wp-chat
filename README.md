# WordPress RAG Chatbot (MVP)

Minimal end-to-end RAG pipeline for a WordPress site: REST fetch → clean → sentence-based chunking → FAISS index → FastAPI chat API.

## Stack
- requests, readability-lxml, BeautifulSoup
- sentence-transformers (all-MiniLM-L6-v2), FAISS (cpu)
- FastAPI + Uvicorn

## Project layout
```
wp-chat/
  .state/                  # conditional GET: Last-Modified / ETag
  data/
    raw/                   # fetched JSON
    clean/                 # cleaned JSONL
    index/                 # FAISS index + meta + (optional) cache
  src/
    fetch_wp.py            # REST fetch with pagination/conditional GET/retries
    clean_text.py          # readability + boilerplate removal
    utils_chunk.py         # JP sentence-first chunking
    build_index.py         # embeddings + FAISS IndexIDMap2
    chat_api.py            # FastAPI /ask
  requirements.txt
  README.md
```

## Prerequisites
- Python 3.10+
- macOS (tested), internet access for model download

## Setup
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Configure
Create `.env` (or export an env var) with your WordPress base URL:
```bash
# .env
WP_BASE_URL=https://your-blog.example.com
```

You can start from `.env.example` and edit it:

```bash
cp .env.example .env
```

## Run pipeline
```bash
# 1) Fetch public posts via REST (pagination + conditional GET + retries)
python src/fetch_wp.py

# 2) Clean HTML → text (readability + boilerplate removal)
python src/clean_text.py

# 3) Build embeddings + FAISS index (JP sentence-first chunking)
python src/build_index.py
```

### Quickstart (all steps)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # edit WP_BASE_URL
python src/fetch_wp.py && python src/clean_text.py && python src/build_index.py
uvicorn src.chat_api:app --reload --port 8080
```

Artifacts:
- data/raw/posts.jsonl
- data/clean/posts_clean.jsonl
- data/index/wp.faiss, data/index/wp.meta.json
- Optional cache: data/index/embeddings.cache.jsonl
- Conditional GET state: .state/last_modified.txt, .state/etag.txt

## Serve API
```bash
uvicorn src.chat_api:app --reload --port 8080
```

### Query example
```bash
curl -s -X POST http://127.0.0.1:8080/ask \
  -H 'Content-Type: application/json' \
  -d '{"question":"プライバシーポリシーは？","topk":5}' | jq
```
Response includes `title`, `url` (source attribution), and a short `snippet`.

## Notes
- Conditional GET: to force a full refetch, delete files under `.state/`.
- Embeddings cache: expensive encodes are cached by chunk SHA-1; delete the cache to recompute.
- Retrieval: normalized embeddings + IndexFlatIP via IndexIDMap2.
- API: `topk` is bounded (1–10); CORS allows `http://localhost:3000`.
- Ethics: start with public content only; always return source URL.
// Git hygiene
- Git: `data/` and `.state/` are ignored by default (see `.gitignore`).
- Large artifacts like `data/index/wp.faiss` should not be committed; use Git LFS if you must version them.
- The API (`src/chat_api.py`) loads the index at import time; if you run the server before building, it will fail. Build the index first or guard the loading in your fork.

## Next
- Extend to pages/custom post types
- Evaluation set (R@k / MRR)
- Smarter chunking (heading-aware)
