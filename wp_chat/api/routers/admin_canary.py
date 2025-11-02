"""Admin Canary router - handles /admin/canary/* endpoints"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

# Import canary management functions
from ...management.canary_manager import (
    clear_emergency_stop,
    disable_canary,
    emergency_stop_canary,
    enable_canary,
    get_canary_status,
    update_canary_rollout,
)

router = APIRouter()


@router.get("/status")
def get_canary_status_endpoint():
    """Get current canary deployment status"""
    try:
        status = get_canary_status()
        return JSONResponse(status)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/rollout")
def update_canary_rollout_endpoint(percentage: float, updated_by: str = "api"):
    """Update canary rollout percentage"""
    try:
        if not 0.0 <= percentage <= 1.0:
            raise HTTPException(400, "Percentage must be between 0.0 and 1.0")

        update_canary_rollout(percentage, updated_by)
        return JSONResponse(
            {"message": f"Canary rollout updated to {percentage:.1%}", "status": "success"}
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/enable")
def enable_canary_endpoint(percentage: float = 0.1, updated_by: str = "api"):
    """Enable canary deployment"""
    try:
        if not 0.0 <= percentage <= 1.0:
            raise HTTPException(400, "Percentage must be between 0.0 and 1.0")

        enable_canary(percentage, updated_by)
        return JSONResponse(
            {"message": f"Canary deployment enabled at {percentage:.1%}", "status": "success"}
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/disable")
def disable_canary_endpoint(updated_by: str = "api"):
    """Disable canary deployment"""
    try:
        disable_canary(updated_by)
        return JSONResponse({"message": "Canary deployment disabled", "status": "success"})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/emergency-stop")
def emergency_stop_canary_endpoint(updated_by: str = "api"):
    """Emergency stop canary deployment"""
    try:
        emergency_stop_canary(updated_by)
        return JSONResponse(
            {
                "message": "Emergency stop activated - rerank disabled for all users",
                "status": "success",
            }
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/clear-emergency")
def clear_emergency_stop_endpoint(updated_by: str = "api"):
    """Clear emergency stop"""
    try:
        clear_emergency_stop(updated_by)
        return JSONResponse({"message": "Emergency stop cleared", "status": "success"})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
