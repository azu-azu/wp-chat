"""Admin Cache router - handles /admin/cache/* endpoints"""
from fastapi import APIRouter
from fastapi.responses import JSONResponse

# Import cache manager
from ...core.cache import cache_manager

router = APIRouter()


@router.post("/clear")
def clear_cache():
    """Clear all cache entries (admin endpoint)"""
    try:
        success = cache_manager.clear()
        return JSONResponse({"success": success, "message": "Cache cleared"})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
