"""Chat router - handles /search, /ask, /generate endpoints"""
import json
import time

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

# Import models
from ...api.models import AskRequest, GenerateRequest, SearchRequest

# Import authentication
from ...core.auth import get_api_key

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
from ...services.cache_service import CacheService
from ...services.generation_service import GenerationService

# Import services (Phase 2)
from ...services.search_service import SearchService

# Global resources (will be initialized by chat_api.py)
model = None
index = None
meta = None
tfidf_vec = None
tfidf_mat = None
TOPK_DEFAULT = None
TOPK_MAX = None

# Service instances (Phase 2)
search_service = None
generation_service = None
cache_service = None


def init_globals(
    model_obj, index_obj, meta_obj, tfidf_vec_obj, tfidf_mat_obj, topk_default, topk_max
):
    """Initialize global resources and services from chat_api.py"""
    global model, index, meta, tfidf_vec, tfidf_mat, TOPK_DEFAULT, TOPK_MAX
    global search_service, generation_service, cache_service

    # Initialize resources
    model = model_obj
    index = index_obj
    meta = meta_obj
    tfidf_vec = tfidf_vec_obj
    tfidf_mat = tfidf_mat_obj
    TOPK_DEFAULT = topk_default
    TOPK_MAX = topk_max

    # Initialize services (Phase 2)
    search_service = SearchService(model, index, meta, tfidf_vec, tfidf_mat)
    generation_service = GenerationService(meta)
    cache_service = CacheService()


router = APIRouter()


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

        # Check cache first (using CacheService)
        cached_results = cache_service.get_search_results(q)
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

        # Perform search (using SearchService)
        # Check canary deployment for rerank decision
        canary_rerank_enabled = is_rerank_enabled_for_user(user_id)
        final_rerank = rerank and canary_rerank_enabled

        search_result = search_service.execute_search(
            query=q, topk=topk, mode=mode, rerank=final_rerank
        )
        rerank_status = search_result.rerank_enabled

        # Convert documents to output format
        out = []
        for doc in search_result.documents:
            result_item = {
                "rank": doc.rank,
                "hybrid_score": doc.hybrid_score,
                "post_id": doc.post_id,
                "chunk_id": doc.chunk_id,
                "title": doc.title,
                "url": doc.url,
            }

            # Add ce_score if available (for A/B analysis)
            if doc.ce_score is not None:
                result_item["ce_score"] = doc.ce_score

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

        # Cache results (using CacheService)
        cache_service.cache_search_results(q, out)

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

    # Perform search (using SearchService)
    search_result = search_service.execute_search(
        query=q, topk=req.topk, mode=mode, rerank=req.rerank
    )
    rerank_status = search_result.rerank_enabled

    # Convert documents to output format
    hits = []
    for doc in search_result.documents:
        hit_item = {
            "rank": doc.rank,
            "hybrid_score": doc.hybrid_score,
            "post_id": doc.post_id,
            "chunk_id": doc.chunk_id,
            "title": doc.title,
            "url": doc.url,
            "snippet": doc.create_snippet(400),
        }

        # Add ce_score if available (for A/B analysis)
        if doc.ce_score is not None:
            hit_item["ce_score"] = doc.ce_score

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

        # Check cache first (using CacheService)
        cache_key = cache_service.build_generation_cache_key(
            req.question, req.topk, req.mode, req.rerank
        )
        cached_result = cache_service.get_generation_result(cache_key)
        if cached_result is not None:
            cache_hit = True
            # For streaming, return cached result as non-streaming
            return JSONResponse(cached_result)

        # Perform retrieval (using SearchService)
        canary_rerank_enabled = is_rerank_enabled_for_user(req.user_id)
        final_rerank = req.rerank and canary_rerank_enabled

        search_result = search_service.execute_search(
            query=req.question, topk=req.topk, mode=req.mode, rerank=final_rerank
        )
        rerank_status = search_result.rerank_enabled

        # Convert domain documents to generation format (using GenerationService)
        docs = generation_service.prepare_from_domain_documents(search_result.documents)

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

                # Cache the result (using CacheService)
                cache_service.cache_generation_result(cache_key, response_data)

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
