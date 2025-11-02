"""Chat router - handles /search, /ask, /generate endpoints"""
import json
import time

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

# Import models
from ...api.models import AskRequest, GenerateRequest, SearchRequest

# Import authentication
from ...core.auth import get_api_key

# Import cache functionality
from ...core.cache import cache_manager, cache_search_results, get_cached_search_results

# Import configuration
from ...core.config import get_config_value

# Import rate limiting
from ...core.rate_limit import check_rate_limit, get_rate_limit_headers

# Import SLO monitoring
from ...core.slo_monitoring import record_api_metric

# Import generation pipeline
from ...generation.generation import generation_pipeline
from ...generation.highlight import highlight_results
from ...generation.openai_client import openai_client

# Import A/B logging
from ...management.ab_logging import ab_logger

# Import canary management
from ...management.canary_manager import get_canary_status, is_rerank_enabled_for_user

# Import retrieval functions
from ...retrieval.rerank import (
    Candidate,
    CrossEncoderReranker,
    dedup_by_article,
    mmr_diversify,
    rerank_with_ce,
)

# Import global resources from parent module
# These will be initialized by chat_api.py
model = None
index = None
meta = None
tfidf_vec = None
tfidf_mat = None
TOPK_DEFAULT = None
TOPK_MAX = None


def init_globals(
    model_obj, index_obj, meta_obj, tfidf_vec_obj, tfidf_mat_obj, topk_default, topk_max
):
    """Initialize global resources from chat_api.py"""
    global model, index, meta, tfidf_vec, tfidf_mat, TOPK_DEFAULT, TOPK_MAX
    model = model_obj
    index = index_obj
    meta = meta_obj
    tfidf_vec = tfidf_vec_obj
    tfidf_mat = tfidf_mat_obj
    TOPK_DEFAULT = topk_default
    TOPK_MAX = topk_max


router = APIRouter()


# Helper functions
def _minmax(x):
    mn, mx = float(x.min()), float(x.max())
    return (x - mn) / (mx - mn + 1e-9)


def _search_dense(q: str, topk: int):
    qv = model.encode(q, normalize_embeddings=True).astype("float32")
    D, I = index.search(np.expand_dims(qv, 0), topk)  # noqa: N806, E741
    return list(zip(I[0].tolist(), D[0].tolist(), strict=True))


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
            candidates.append(
                Candidate(
                    doc_id=m["url"],
                    chunk_id=m["chunk_id"],
                    text=m["chunk"],
                    hybrid_score=float(score),
                    emb=doc_emb,
                    meta={"post_id": m["post_id"], "title": m["title"], "url": m["url"]},
                )
            )

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


# Endpoints
@router.post("/search")
def search(
    req: SearchRequest,
    user_id: str = "anonymous",
    highlight: bool = True,
    request: Request = None,
    api_key: str = Depends(get_api_key),
):
    start_time = time.time()
    status_code = 200
    cache_hit = False
    fallback_used = False
    error_message = None
    q = req.query
    topk = req.topk
    mode = req.mode
    rerank = req.rerank

    try:
        if not q.strip():
            raise HTTPException(400, "query is empty")

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
                return JSONResponse(
                    {
                        "query": q,
                        "mode": mode,
                        "rerank": False,
                        "highlight": highlight,
                        "cached": True,
                        "contexts": cached_results,
                    }
                )

        if mode == "dense":
            hits = _search_dense(q, topk)
            rerank_status = False
        elif mode == "bm25":
            hits = _search_bm25(q, topk)
            rerank_status = False
        else:
            # Check canary deployment for rerank decision
            canary_rerank_enabled = is_rerank_enabled_for_user(user_id)
            # Use canary decision if rerank is not explicitly disabled
            final_rerank = rerank and canary_rerank_enabled
            hits, rerank_status = _search_hybrid_with_rerank(q, topk, rerank=final_rerank)

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
                "url": m["url"],
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
                ip_address=request.client.host if request and request.client else None,
            )
        except Exception:
            pass  # Don't fail the request if logging fails

        # Cache results if caching is enabled
        if get_config_value("api.cache.enabled", True):
            search_ttl = get_config_value("api.cache.search_ttl", 1800)
            cache_search_results(q, out, search_ttl)

        return JSONResponse(
            {
                "q": q,
                "mode": mode,
                "rerank": rerank_status,
                "highlight": highlight,
                "contexts": out,
                "canary": {
                    "user_id": user_id,
                    "rerank_enabled": canary_rerank_enabled,
                    "rollout_percentage": get_canary_status()
                    .get("config", {})
                    .get("rollout_percentage", 0.0),
                },
            }
        )

    except HTTPException as e:
        status_code = e.status_code
        error_message = str(e.detail)
        raise e
    except Exception as e:
        status_code = 500
        error_message = str(e)
        fallback_used = True
        raise HTTPException(500, f"Internal server error: {str(e)}") from e
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
            error_message=error_message,
        )


@router.post("/ask")
def ask(req: AskRequest, api_key: str = Depends(get_api_key)):
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
            "snippet": snip,
        }

        # Add ce_score if available (for A/B analysis)
        if ce_sc is not None:
            hit_item["ce_score"] = ce_sc

        hits.append(hit_item)

    # Apply highlighting if requested
    if req.highlight:
        hits = highlight_results(
            hits, q, get_config_value("api.snippet_length", 400), use_morphology=req.use_morphology
        )

    return JSONResponse(
        {
            "question": q,
            "mode": mode,
            "rerank": rerank_status,
            "highlight": req.highlight,
            "contexts": hits,
        }
    )


@router.post("/generate")
async def generate(
    req: GenerateRequest, request: Request = None, api_key: str = Depends(get_api_key)
):
    """Generate RAG response with streaming support"""
    start_time = time.time()
    status_code = 200
    cache_hit = False
    fallback_used = False
    error_message = None
    generation_metrics = None

    try:
        if not req.question.strip():
            raise HTTPException(400, "question is empty")

        # Rate limiting check
        if get_config_value("api.rate_limit.enabled", True):
            max_requests = get_config_value(
                "api.rate_limit.max_requests", 50
            )  # Lower limit for generation
            window_seconds = get_config_value("api.rate_limit.window_seconds", 3600)

            is_allowed, rate_info = check_rate_limit(request, max_requests, window_seconds)
            if not is_allowed:
                headers = get_rate_limit_headers(rate_info)
                raise HTTPException(429, "Rate limit exceeded", headers=headers)

        # Check cache first
        cache_key = f"generate:{req.question}:{req.topk}:{req.mode}:{req.rerank}"
        if get_config_value("api.cache.enabled", True):
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                cache_hit = True
                if req.stream:
                    # For streaming, return cached result as non-streaming
                    return JSONResponse(cached_result)
                else:
                    return JSONResponse(cached_result)

        # Perform retrieval using existing hybrid search
        if req.mode == "dense":
            hits = _search_dense(req.question, req.topk)
            rerank_status = False
        elif req.mode == "bm25":
            hits = _search_bm25(req.question, req.topk)
            rerank_status = False
        else:
            # Check canary deployment for rerank decision
            canary_rerank_enabled = is_rerank_enabled_for_user(req.user_id)
            final_rerank = req.rerank and canary_rerank_enabled
            hits, rerank_status = _search_hybrid_with_rerank(
                req.question, req.topk, rerank=final_rerank
            )

        # Convert hits to document format
        docs = []
        for rank, hit in enumerate(hits, 1):
            if len(hit) == 3:  # (idx, hybrid_score, ce_score)
                idx, hybrid_sc, ce_sc = hit
            else:  # (idx, score) - backward compatibility
                idx, hybrid_sc = hit
                ce_sc = None

            if idx < 0 or idx >= len(meta):
                continue

            m = meta[idx]
            doc = {
                "rank": rank,
                "hybrid_score": hybrid_sc,
                "post_id": m["post_id"],
                "chunk_id": m["chunk_id"],
                "title": m["title"],
                "url": m["url"],
                "snippet": m["chunk"][:400] + ("…" if len(m["chunk"]) > 400 else ""),
                "chunk": m["chunk"],
            }

            if ce_sc is not None:
                doc["ce_score"] = ce_sc

            docs.append(doc)

        # Process context and build prompt
        processed_docs, context_metadata = generation_pipeline.process_retrieval_results(docs)
        messages, prompt_stats = generation_pipeline.build_prompt(req.question, processed_docs)

        if req.stream:
            # Streaming response
            async def generate_stream():
                nonlocal generation_metrics, fallback_used, error_message
                try:
                    full_response = ""
                    async for chunk in openai_client.stream_chat(messages):
                        if chunk["type"] == "delta":
                            content = chunk["content"]
                            full_response += content
                            yield f"data: {json.dumps({'type': 'delta', 'content': content})}\n\n"

                        elif chunk["type"] == "metrics":
                            generation_metrics = chunk
                            yield f"data: {json.dumps({'type': 'metrics', 'ttft_ms': chunk['ttft_ms'], 'model': chunk['model']})}\n\n"

                        elif chunk["type"] == "done":
                            # Post-process response
                            result = generation_pipeline.post_process_response(
                                full_response, processed_docs
                            )

                            # Send references
                            yield f"data: {json.dumps({'type': 'refs', 'value': result.references})}\n\n"

                            # Send final metrics
                            metrics = chunk["metrics"]
                            metrics.update(
                                {
                                    "citation_count": result.metadata["citation_count"],
                                    "has_citations": result.metadata["has_citations"],
                                    "context_metadata": context_metadata,
                                    "prompt_stats": prompt_stats,
                                }
                            )
                            yield f"data: {json.dumps({'type': 'done', 'metrics': metrics})}\n\n"

                        elif chunk["type"] == "error":
                            generation_metrics = chunk["metrics"]
                            fallback_used = True

                            # Use fallback response
                            result = generation_pipeline.generate_fallback_response(
                                req.question, processed_docs
                            )
                            yield f"data: {json.dumps({'type': 'error', 'error': chunk['error'], 'fallback': result.answer})}\n\n"
                            yield f"data: {json.dumps({'type': 'refs', 'value': result.references})}\n\n"
                            yield f"data: {json.dumps({'type': 'done', 'metrics': generation_metrics})}\n\n"

                except Exception as e:
                    error_message = str(e)
                    fallback_used = True

                    result = generation_pipeline.generate_fallback_response(
                        req.question, processed_docs
                    )
                    yield f"data: {json.dumps({'type': 'error', 'error': str(e), 'fallback': result.answer})}\n\n"
                    yield f"data: {json.dumps({'type': 'refs', 'value': result.references})}\n\n"
                    yield f"data: {json.dumps({'type': 'done', 'metrics': {'success': False, 'error_message': str(e)}})}\n\n"

            return StreamingResponse(
                generate_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",  # Disable nginx buffering
                },
            )

        else:
            # Non-streaming response
            try:
                content, metrics = await openai_client.chat_completion(messages)
                generation_metrics = metrics

                if metrics.success:
                    # Post-process response
                    result = generation_pipeline.post_process_response(content, processed_docs)

                    response_data = {
                        "answer": result.answer,
                        "references": result.references,
                        "metadata": {
                            "latency_ms": metrics.total_latency_ms,
                            "ttft_ms": metrics.ttft_ms,
                            "token_count": metrics.token_usage.total_tokens,
                            "model": metrics.model,
                            "citation_count": result.metadata["citation_count"],
                            "has_citations": result.metadata["has_citations"],
                            "context_metadata": context_metadata,
                            "prompt_stats": prompt_stats,
                            "rerank_enabled": rerank_status,
                        },
                    }
                else:
                    # Use fallback
                    fallback_used = True
                    result = generation_pipeline.generate_fallback_response(
                        req.question, processed_docs
                    )
                    response_data = {
                        "answer": result.answer,
                        "references": result.references,
                        "metadata": {
                            "latency_ms": metrics.total_latency_ms,
                            "ttft_ms": metrics.ttft_ms,
                            "token_count": 0,
                            "model": metrics.model,
                            "fallback": True,
                            "error_message": metrics.error_message,
                            "context_metadata": context_metadata,
                            "prompt_stats": prompt_stats,
                            "rerank_enabled": rerank_status,
                        },
                    }

                # Cache the result
                if get_config_value("api.cache.enabled", True):
                    cache_ttl = get_config_value("api.cache.search_ttl", 1800)
                    cache_manager.set(cache_key, response_data, cache_ttl)

                return JSONResponse(response_data)

            except Exception as e:
                fallback_used = True
                error_message = str(e)
                result = generation_pipeline.generate_fallback_response(
                    req.question, processed_docs
                )

                response_data = {
                    "answer": result.answer,
                    "references": result.references,
                    "metadata": {
                        "latency_ms": int((time.time() - start_time) * 1000),
                        "ttft_ms": 0,
                        "token_count": 0,
                        "model": "fallback",
                        "fallback": True,
                        "error_message": str(e),
                        "context_metadata": context_metadata,
                        "prompt_stats": prompt_stats,
                        "rerank_enabled": rerank_status,
                    },
                }

                return JSONResponse(response_data)

    except HTTPException as e:
        status_code = e.status_code
        error_message = str(e.detail)
        raise e
    except Exception as e:
        status_code = 500
        error_message = str(e)
        fallback_used = True
        raise HTTPException(500, f"Internal server error: {str(e)}") from e
    finally:
        # Record SLO metrics
        latency_ms = int((time.time() - start_time) * 1000)
        record_api_metric(
            endpoint="generate",
            latency_ms=latency_ms,
            status_code=status_code,
            rerank_enabled=req.rerank if "req" in locals() else False,
            cache_hit=cache_hit,
            fallback_used=fallback_used,
            error_message=error_message,
            generation_metrics=generation_metrics.__dict__ if generation_metrics else None,
        )
