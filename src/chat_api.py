import os, json, numpy as np, faiss
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, conint
from sentence_transformers import SentenceTransformer
from fastapi.responses import JSONResponse, HTMLResponse
from sklearn.feature_extraction.text import TfidfVectorizer
from scipy.sparse import load_npz
import joblib
from .rerank import CrossEncoderReranker, mmr_diversify, rerank_with_ce, dedup_by_article, Candidate
from .highlight import highlight_results, get_highlight_info
from .config import get_config_value
from .ab_logging import ab_logger, ab_logging_middleware, get_ab_stats
from .model_manager import get_device_status
from .cache import cache_manager, cache_search_results, get_cached_search_results
from .rate_limit import check_rate_limit, get_rate_limit_headers, rate_limiter
from .slo_monitoring import record_api_metric, get_slo_status, get_metrics_summary
from .dashboard import get_dashboard_data, get_ab_summary, get_cache_summary, get_performance_summary

IDX = "data/index/wp.faiss"
META = "data/index/wp.meta.json"
MODEL = "all-MiniLM-L6-v2"
TOPK_DEFAULT = get_config_value("api.topk_default", 5)
TOPK_MAX = get_config_value("api.topk_max", 10)
TFIDF_VEC = "data/index/wp.tfidf.pkl"
TFIDF_MAT = "data/index/wp.tfidf.npz"

class AskReq(BaseModel):
    question: str
    topk: conint(ge=1, le=TOPK_MAX) = TOPK_DEFAULT
    mode: str = "hybrid"  # dense|bm25|hybrid
    rerank: bool = False
    highlight: bool = True  # Enable query highlighting
    use_morphology: bool = True  # Use morphological analysis for Japanese

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add A/B logging middleware
app.middleware("http")(ab_logging_middleware)
model = SentenceTransformer(MODEL)
index = faiss.read_index(IDX)
meta = json.load(open(META, "r", encoding="utf-8"))
tfidf_vec = joblib.load(TFIDF_VEC) if os.path.exists(TFIDF_VEC) else None
tfidf_mat = load_npz(TFIDF_MAT) if os.path.exists(TFIDF_MAT) else None

def _minmax(x):
    mn, mx = float(x.min()), float(x.max())
    return (x - mn) / (mx - mn + 1e-9)

def _search_dense(q: str, topk: int):
    qv = model.encode(q, normalize_embeddings=True).astype("float32")
    D, I = index.search(np.expand_dims(qv, 0), topk)
    return list(zip(I[0].tolist(), D[0].tolist()))

def _search_bm25(q: str, topk: int):
    if tfidf_vec is None or tfidf_mat is None:
        raise HTTPException(400, "BM25 index not built. Run build_bm25.py.")
    qv = tfidf_vec.transform([q])
    scores = (tfidf_mat @ qv.T).toarray().ravel()
    ids = np.argsort(-scores)[:topk]
    return [(int(i), float(scores[i])) for i in ids]

def _search_hybrid_with_rerank(q: str, topk: int, wd=0.6, wb=0.4, rerank=False, mmr_lambda=0.7):
    """Enhanced hybrid search with optional reranking"""
    d = _search_dense(q, 200)
    b = _search_bm25(q, 200)
    ids = sorted(set([i for i, _ in d] + [i for i, _ in b]))
    d_map = {i: s for i, s in d}
    b_map = {i: s for i, s in b}
    d_arr = np.array([d_map.get(i, 0.0) for i in ids], dtype="float32")
    b_arr = np.array([b_map.get(i, 0.0) for i in ids], dtype="float32")
    combo = wd * _minmax(d_arr) + wb * _minmax(b_arr)

    # Create Candidate objects
    candidates = []
    for i, score in enumerate(combo):
        if i < len(meta):
            m = meta[i]
            doc_emb = model.encode(m["chunk"], normalize_embeddings=True).astype("float32")
            candidates.append(Candidate(
                doc_id=m["url"],
                chunk_id=m["chunk_id"],
                text=m["chunk"],
                hybrid_score=float(score),
                emb=doc_emb,
                meta={"post_id": m["post_id"], "title": m["title"], "url": m["url"]}
            ))

    # Article deduplication
    candidates = dedup_by_article(candidates, limit_per_article=5)

    # MMR diversification
    q_emb = model.encode(q, normalize_embeddings=True).astype("float32")
    diversified = mmr_diversify(q_emb, candidates, lambda_=mmr_lambda, topn=30)

    # Reranking
    if rerank:
        try:
            ce = CrossEncoderReranker("cross-encoder/ms-marco-MiniLM-L-6-v2", batch_size=16)
            ranked = rerank_with_ce(q, diversified, ce, topk=topk, timeout_sec=5.0)
            rerank_status = True
        except Exception as e:
            # Fallback to hybrid scores
            ranked = sorted(diversified, key=lambda c: c.hybrid_score, reverse=True)[:topk]
            rerank_status = False
            print(f"Reranking failed: {e}")
    else:
        ranked = sorted(diversified, key=lambda c: c.hybrid_score, reverse=True)[:topk]
        rerank_status = False

    # Convert back to (idx, score, ce_score) format
    results = []
    for cand in ranked:
        # Find original index in meta
        for i, m in enumerate(meta):
            if m["url"] == cand.doc_id and m["chunk_id"] == cand.chunk_id:
                ce_score = cand.meta.get("ce_score", None)
                results.append((i, cand.hybrid_score, ce_score))
                break

    return results, rerank_status

@app.get("/search")
def search(q: str, topk: conint(ge=1, le=TOPK_MAX) = TOPK_DEFAULT, mode: str = "hybrid", rerank: bool = False, highlight: bool = True, request: Request = None):
    start_time = time.time()
    status_code = 200
    cache_hit = False
    fallback_used = False
    error_message = None

    try:
        if not q.strip():
            raise HTTPException(400, "q is empty")

        # Rate limiting check
        if get_config_value("api.rate_limit.enabled", True):
            max_requests = get_config_value("api.rate_limit.max_requests", 100)
            window_seconds = get_config_value("api.rate_limit.window_seconds", 3600)

            is_allowed, rate_info = check_rate_limit(request, max_requests, window_seconds)
            if not is_allowed:
                headers = get_rate_limit_headers(rate_info)
                raise HTTPException(429, "Rate limit exceeded", headers=headers)

        # Check cache first
        if get_config_value("api.cache.enabled", True):
            cached_results = get_cached_search_results(q)
            if cached_results is not None:
                cache_hit = True
                return JSONResponse({
                    "query": q,
                    "mode": mode,
                    "rerank": False,
                    "highlight": highlight,
                    "cached": True,
                    "contexts": cached_results
                })
        if mode == "dense":
            hits = _search_dense(q, topk)
            rerank_status = False
        elif mode == "bm25":
            hits = _search_bm25(q, topk)
            rerank_status = False
        else:
            hits, rerank_status = _search_hybrid_with_rerank(q, topk, rerank=rerank)
        out = []
        for rank, hit in enumerate(hits, 1):
            if len(hit) == 3:  # (idx, hybrid_score, ce_score)
                idx, hybrid_sc, ce_sc = hit
            else:  # (idx, score) - backward compatibility
                idx, hybrid_sc = hit
                ce_sc = None

            if idx < 0 or idx >= len(meta):
                continue
            m = meta[idx]

        result_item = {
            "rank": rank,
            "hybrid_score": hybrid_sc,
            "post_id": m["post_id"],
            "chunk_id": m["chunk_id"],
            "title": m["title"],
            "url": m["url"]
        }

        # Add ce_score if available (for A/B analysis)
        if ce_sc is not None:
            result_item["ce_score"] = ce_sc

        out.append(result_item)

        # Apply highlighting if requested
        if highlight:
            out = highlight_results(out, q, get_config_value("api.snippet_length", 400))

        # Log A/B metrics (additional logging for detailed analysis)
        try:
            ab_logger.log_search_metrics(
                query=q,
                rerank_enabled=rerank_status,
                latency_ms=0,  # Will be updated by middleware
                result_count=len(out),
                mode=mode,
                topk=topk,
                user_agent=request.headers.get("user-agent") if request else None,
                ip_address=request.client.host if request and request.client else None
            )
        except Exception as e:
            pass  # Don't fail the request if logging fails

        # Cache results if caching is enabled
        if get_config_value("api.cache.enabled", True):
            search_ttl = get_config_value("api.cache.search_ttl", 1800)
            cache_search_results(q, out, search_ttl)

        return JSONResponse({"q": q, "mode": mode, "rerank": rerank_status, "highlight": highlight, "contexts": out})

    except HTTPException as e:
        status_code = e.status_code
        error_message = str(e.detail)
        raise e
    except Exception as e:
        status_code = 500
        error_message = str(e)
        fallback_used = True
        raise HTTPException(500, f"Internal server error: {str(e)}")
    finally:
        # Record SLO metrics
        latency_ms = int((time.time() - start_time) * 1000)
        record_api_metric(
            endpoint="search",
            latency_ms=latency_ms,
            status_code=status_code,
            rerank_enabled=rerank,
            cache_hit=cache_hit,
            fallback_used=fallback_used,
            error_message=error_message
        )

@app.post("/ask")
def ask(req: AskReq):
    q = req.question.strip()
    if not q:
        raise HTTPException(400, "question is empty")
    mode = req.mode
    if mode == "dense":
        pairs = _search_dense(q, req.topk)
        rerank_status = False
    elif mode == "bm25":
        pairs = _search_bm25(q, req.topk)
        rerank_status = False
    else:
        pairs, rerank_status = _search_hybrid_with_rerank(q, req.topk, rerank=req.rerank)
    hits = []
    for rank, hit in enumerate(pairs, 1):
        if len(hit) == 3:  # (idx, hybrid_score, ce_score)
            idx, hybrid_sc, ce_sc = hit
        else:  # (idx, score) - backward compatibility
            idx, hybrid_sc = hit
            ce_sc = None

        if idx < 0 or idx >= len(meta):
            continue
        m = meta[idx]
        chunk = m["chunk"]
        snip = chunk[:400] + ("…" if len(chunk) > 400 else "")

        hit_item = {
            "rank": rank,
            "hybrid_score": hybrid_sc,
            "post_id": m["post_id"],
            "chunk_id": m["chunk_id"],
            "title": m["title"],
            "url": m["url"],
            "snippet": snip
        }

        # Add ce_score if available (for A/B analysis)
        if ce_sc is not None:
            hit_item["ce_score"] = ce_sc

        hits.append(hit_item)

    # Apply highlighting if requested
    if req.highlight:
        hits = highlight_results(hits, q, get_config_value("api.snippet_length", 400),
                                use_morphology=req.use_morphology)

    return JSONResponse({"question": q, "mode": mode, "rerank": rerank_status, "highlight": req.highlight, "contexts": hits})

@app.get("/stats/ab")
def get_ab_statistics(days: int = 7):
    """Get A/B testing statistics"""
    stats = get_ab_stats(days)
    return JSONResponse(stats)

@app.get("/stats/health")
def health_check():
    """Health check endpoint"""
    return JSONResponse({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    })

@app.get("/stats/highlight")
def get_highlight_info_endpoint(query: str):
    """Get highlighting information for a query"""
    try:
        info = get_highlight_info(query)
        return JSONResponse({
            "query": query,
            "morphology_available": info["morphology_available"],
            "extracted_keywords": info["extracted_keywords"],
            "morphology_keywords": info["morphology_keywords"],
            "basic_keywords": info["basic_keywords"]
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/stats/cache")
def get_cache_stats():
    """Get cache statistics"""
    try:
        stats = cache_manager.get_stats()
        return JSONResponse(stats)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/stats/rate-limit")
def get_rate_limit_stats():
    """Get rate limiting statistics"""
    try:
        stats = rate_limiter.get_global_stats()
        return JSONResponse(stats)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/stats/dashboard")
def get_dashboard_statistics(days: int = 7, hours: int = 24):
    """Get comprehensive dashboard data"""
    try:
        dashboard_data = get_dashboard_data(days, hours)
        return JSONResponse(dashboard_data)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/stats/ab-summary")
def get_ab_summary_statistics(days: int = 7):
    """Get A/B testing summary"""
    try:
        summary = get_ab_summary(days)
        return JSONResponse(summary)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/stats/cache-summary")
def get_cache_summary_statistics(hours: int = 24):
    """Get cache efficiency summary"""
    try:
        summary = get_cache_summary(hours)
        return JSONResponse(summary)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/stats/performance-summary")
def get_performance_summary_statistics(hours: int = 24):
    """Get performance trends summary"""
    try:
        summary = get_performance_summary(hours)
        return JSONResponse(summary)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/dashboard")
def serve_dashboard():
    """Serve the dashboard HTML page"""
    try:
        with open("dashboard.html", "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        return JSONResponse({"error": "Dashboard file not found"}, status_code=404)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/stats/slo")
def get_slo_statistics():
    """Get SLO monitoring statistics"""
    try:
        slo_status = get_slo_status()
        return JSONResponse(slo_status)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/stats/metrics")
def get_metrics_statistics(hours: int = 24):
    """Get metrics summary for the last N hours"""
    try:
        summary = get_metrics_summary(hours)
        return JSONResponse(summary)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/admin/cache/clear")
def clear_cache():
    """Clear all cache entries (admin endpoint)"""
    try:
        success = cache_manager.clear()
        return JSONResponse({"success": success, "message": "Cache cleared"})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/stats/device")
def device_status():
    """Get device and model information"""
    device_info = get_device_status()
    return JSONResponse(device_info)
