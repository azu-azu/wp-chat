import os, json, numpy as np, faiss
from datetime import datetime
from typing import List
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
from .canary_manager import (is_rerank_enabled_for_user, update_canary_rollout, enable_canary,
                           disable_canary, emergency_stop_canary, clear_emergency_stop, get_canary_status)
from .runbook import (detect_incident, get_emergency_procedures, execute_emergency_action,
                     resolve_incident, get_active_incidents, get_incident_summary,
                     auto_detect_incidents, IncidentType, Severity, EmergencyAction)
from .backup_manager import (create_backup, restore_backup, list_backups, get_backup_statistics,
                           cleanup_old_backups, schedule_backup, BackupInfo, RestoreInfo)

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
def search(q: str, topk: conint(ge=1, le=TOPK_MAX) = TOPK_DEFAULT, mode: str = "hybrid", rerank: bool = False, highlight: bool = True, user_id: str = "anonymous", request: Request = None):
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

        return JSONResponse({
            "q": q,
            "mode": mode,
            "rerank": rerank_status,
            "highlight": highlight,
            "contexts": out,
            "canary": {
                "user_id": user_id,
                "rerank_enabled": canary_rerank_enabled,
                "rollout_percentage": get_canary_status().get("config", {}).get("rollout_percentage", 0.0)
            }
        })

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

# Canary Management Endpoints
@app.get("/admin/canary/status")
def get_canary_status_endpoint():
    """Get current canary deployment status"""
    try:
        status = get_canary_status()
        return JSONResponse(status)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/admin/canary/rollout")
def update_canary_rollout_endpoint(percentage: float, updated_by: str = "api"):
    """Update canary rollout percentage"""
    try:
        if not 0.0 <= percentage <= 1.0:
            raise HTTPException(400, "Percentage must be between 0.0 and 1.0")

        update_canary_rollout(percentage, updated_by)
        return JSONResponse({
            "message": f"Canary rollout updated to {percentage:.1%}",
            "status": "success"
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/admin/canary/enable")
def enable_canary_endpoint(percentage: float = 0.1, updated_by: str = "api"):
    """Enable canary deployment"""
    try:
        if not 0.0 <= percentage <= 1.0:
            raise HTTPException(400, "Percentage must be between 0.0 and 1.0")

        enable_canary(percentage, updated_by)
        return JSONResponse({
            "message": f"Canary deployment enabled at {percentage:.1%}",
            "status": "success"
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/admin/canary/disable")
def disable_canary_endpoint(updated_by: str = "api"):
    """Disable canary deployment"""
    try:
        disable_canary(updated_by)
        return JSONResponse({
            "message": "Canary deployment disabled",
            "status": "success"
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/admin/canary/emergency-stop")
def emergency_stop_canary_endpoint(updated_by: str = "api"):
    """Emergency stop canary deployment"""
    try:
        emergency_stop_canary(updated_by)
        return JSONResponse({
            "message": "Emergency stop activated - rerank disabled for all users",
            "status": "success"
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/admin/canary/clear-emergency")
def clear_emergency_stop_endpoint(updated_by: str = "api"):
    """Clear emergency stop"""
    try:
        clear_emergency_stop(updated_by)
        return JSONResponse({
            "message": "Emergency stop cleared",
            "status": "success"
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

# Incident Response Runbook Endpoints
@app.get("/admin/incidents/status")
def get_incident_status():
    """Get current incident status and summary"""
    try:
        summary = get_incident_summary()
        return JSONResponse(summary)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/admin/incidents/active")
def get_active_incidents_endpoint():
    """Get all active incidents"""
    try:
        incidents = get_active_incidents()
        return JSONResponse({
            "active_incidents": [incident.__dict__ for incident in incidents]
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/admin/incidents/detect")
def detect_incident_endpoint(incident_type: str, severity: str, description: str = "",
                           affected_components: List[str] = None):
    """Manually detect an incident"""
    try:
        incident_type_enum = IncidentType(incident_type)
        severity_enum = Severity(severity)

        incident = detect_incident(
            incident_type=incident_type_enum,
            severity=severity_enum,
            description=description,
            affected_components=affected_components or []
        )

        return JSONResponse({
            "message": f"Incident {incident.incident_id} detected",
            "incident": incident.__dict__
        })
    except ValueError as e:
        return JSONResponse({"error": f"Invalid incident type or severity: {e}"}, status_code=400)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/admin/incidents/{incident_id}/procedures")
def get_incident_procedures(incident_id: str):
    """Get emergency procedures for an incident"""
    try:
        # Find incident
        incidents = get_active_incidents()
        incident = next((inc for inc in incidents if inc.incident_id == incident_id), None)

        if not incident:
            return JSONResponse({"error": "Incident not found"}, status_code=404)

        procedures = get_emergency_procedures(incident.incident_type)

        return JSONResponse({
            "incident_id": incident_id,
            "incident_type": incident.incident_type.value,
            "procedures": [procedure.__dict__ for procedure in procedures]
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/admin/incidents/{incident_id}/execute")
def execute_incident_action(incident_id: str, action_id: str, confirm: bool = False):
    """Execute an emergency action for an incident"""
    try:
        # Find incident
        incidents = get_active_incidents()
        incident = next((inc for inc in incidents if inc.incident_id == incident_id), None)

        if not incident:
            return JSONResponse({"error": "Incident not found"}, status_code=404)

        # Get procedures
        procedures = get_emergency_procedures(incident.incident_type)
        action = next((proc for proc in procedures if proc.action_id == action_id), None)

        if not action:
            return JSONResponse({"error": "Action not found"}, status_code=404)

        # Execute action
        success, output = execute_emergency_action(action, incident, confirm)

        return JSONResponse({
            "success": success,
            "output": output,
            "action": action.__dict__
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/admin/incidents/{incident_id}/resolve")
def resolve_incident_endpoint(incident_id: str, resolution_notes: str = "", assigned_to: str = ""):
    """Mark an incident as resolved"""
    try:
        success = resolve_incident(incident_id, resolution_notes, assigned_to)

        if success:
            return JSONResponse({
                "message": f"Incident {incident_id} resolved",
                "status": "success"
            })
        else:
            return JSONResponse({"error": "Incident not found"}, status_code=404)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/admin/incidents/auto-detect")
def auto_detect_incidents_endpoint():
    """Automatically detect incidents from SLO status"""
    try:
        slo_status = get_slo_status()
        detected_incidents = auto_detect_incidents(slo_status)

        return JSONResponse({
            "message": f"Detected {len(detected_incidents)} incidents",
            "incidents": [incident.__dict__ for incident in detected_incidents]
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

# Backup Management Endpoints
@app.get("/admin/backup/status")
def get_backup_status():
    """Get backup status and statistics"""
    try:
        stats = get_backup_statistics()
        return JSONResponse(stats)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/admin/backup/list")
def list_backups_endpoint(backup_type: str = None):
    """List available backups"""
    try:
        backups = list_backups(backup_type)
        return JSONResponse({
            "backups": [backup.__dict__ for backup in backups]
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/admin/backup/create")
def create_backup_endpoint(backup_type: str = "full", description: str = ""):
    """Create a new backup"""
    try:
        if backup_type not in ["full", "incremental", "index", "cache", "config"]:
            raise HTTPException(400, "Invalid backup type")

        backup = create_backup(backup_type, description)
        return JSONResponse({
            "message": f"Backup created: {backup.backup_id}",
            "backup": backup.__dict__
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/admin/backup/restore")
def restore_backup_endpoint(backup_id: str, target_path: str = None, verify: bool = True):
    """Restore from backup"""
    try:
        restore = restore_backup(backup_id, target_path, verify)
        return JSONResponse({
            "message": f"Restore completed: {restore.restore_id}",
            "restore": restore.__dict__
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.delete("/admin/backup/{backup_id}")
def delete_backup_endpoint(backup_id: str):
    """Delete a backup"""
    try:
        from .backup_manager import backup_manager
        success = backup_manager.delete_backup(backup_id)

        if success:
            return JSONResponse({
                "message": f"Backup deleted: {backup_id}",
                "status": "success"
            })
        else:
            return JSONResponse({"error": "Backup not found"}, status_code=404)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/admin/backup/cleanup")
def cleanup_backups_endpoint():
    """Clean up old backups"""
    try:
        deleted_count = cleanup_old_backups()
        return JSONResponse({
            "message": f"Cleaned up {deleted_count} old backups",
            "deleted_count": deleted_count
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@app.post("/admin/backup/schedule")
def schedule_backup_endpoint():
    """Schedule automatic backup"""
    try:
        backup = schedule_backup()
        if backup:
            return JSONResponse({
                "message": f"Scheduled backup created: {backup.backup_id}",
                "backup": backup.__dict__
            })
        else:
            return JSONResponse({
                "message": "No backup needed at this time",
                "backup": None
            })
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
