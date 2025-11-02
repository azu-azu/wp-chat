"""Stats router - handles /stats/* and /dashboard endpoints"""
from datetime import datetime

from fastapi import APIRouter
from fastapi.responses import JSONResponse

# Import dependencies
from ...core.cache import cache_manager
from ...core.rate_limit import rate_limiter
from ...core.slo_monitoring import get_metrics_summary, get_slo_status
from ...generation.highlight import get_highlight_info
from ...management.ab_logging import get_ab_stats
from ...management.dashboard import (
    get_ab_summary,
    get_cache_summary,
    get_dashboard_data,
    get_performance_summary,
)
from ...management.model_manager import get_device_status

router = APIRouter()


@router.get("/ab")
def get_ab_statistics(days: int = 7):
    """Get A/B testing statistics"""
    stats = get_ab_stats(days)
    return JSONResponse(stats)


@router.get("/health")
def health_check():
    """Health check endpoint"""
    return JSONResponse(
        {"status": "healthy", "timestamp": datetime.now().isoformat(), "version": "1.0.0"}
    )


@router.get("/highlight")
def get_highlight_info_endpoint(query: str):
    """Get highlighting information for a query"""
    try:
        info = get_highlight_info(query)
        return JSONResponse(
            {
                "query": query,
                "morphology_available": info["morphology_available"],
                "extracted_keywords": info["extracted_keywords"],
                "morphology_keywords": info["morphology_keywords"],
                "basic_keywords": info["basic_keywords"],
            }
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/cache")
def get_cache_stats():
    """Get cache statistics"""
    try:
        stats = cache_manager.get_stats()
        return JSONResponse(stats)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/rate-limit")
def get_rate_limit_stats():
    """Get rate limiting statistics"""
    try:
        stats = rate_limiter.get_global_stats()
        return JSONResponse(stats)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/dashboard")
def get_dashboard_statistics(days: int = 7, hours: int = 24):
    """Get comprehensive dashboard data"""
    try:
        dashboard_data = get_dashboard_data(days, hours)
        return JSONResponse(dashboard_data)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/ab-summary")
def get_ab_summary_statistics(days: int = 7):
    """Get A/B testing summary"""
    try:
        summary = get_ab_summary(days)
        return JSONResponse(summary)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/cache-summary")
def get_cache_summary_statistics(hours: int = 24):
    """Get cache efficiency summary"""
    try:
        summary = get_cache_summary(hours)
        return JSONResponse(summary)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/performance-summary")
def get_performance_summary_statistics(hours: int = 24):
    """Get performance trends summary"""
    try:
        summary = get_performance_summary(hours)
        return JSONResponse(summary)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/slo")
def get_slo_statistics():
    """Get SLO monitoring statistics"""
    try:
        slo_status = get_slo_status()
        return JSONResponse(slo_status)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/metrics")
def get_metrics_statistics(hours: int = 24):
    """Get metrics summary for the last N hours"""
    try:
        summary = get_metrics_summary(hours)
        return JSONResponse(summary)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/device")
def device_status():
    """Get device and model information"""
    device_info = get_device_status()
    return JSONResponse(device_info)
