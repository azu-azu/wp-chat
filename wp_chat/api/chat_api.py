import json
import os
from datetime import datetime

import faiss
import joblib
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from scipy.sparse import load_npz
from sentence_transformers import SentenceTransformer

# New imports for improvements
from ..core.cache import cache_manager
from ..core.config import get_config_value
from ..core.exceptions import WPChatException, get_status_code
from ..core.logging_config import setup_logging
from ..core.rate_limit import rate_limiter
from ..core.runbook import (
    IncidentType,
    Severity,
    auto_detect_incidents,
    detect_incident,
    execute_emergency_action,
    get_active_incidents,
    get_emergency_procedures,
    get_incident_summary,
    resolve_incident,
)
from ..core.slo_monitoring import get_metrics_summary, get_slo_status
from ..generation.highlight import get_highlight_info
from ..management.ab_logging import ab_logging_middleware, get_ab_stats
from ..management.backup_manager import (
    cleanup_old_backups,
    create_backup,
    get_backup_statistics,
    list_backups,
    restore_backup,
    schedule_backup,
)
from ..management.canary_manager import (
    clear_emergency_stop,
    disable_canary,
    emergency_stop_canary,
    enable_canary,
    get_canary_status,
    update_canary_rollout,
)
from ..management.dashboard import (
    get_ab_summary,
    get_cache_summary,
    get_dashboard_data,
    get_performance_summary,
)
from ..management.model_manager import get_device_status

# Load environment variables from .env file
load_dotenv()

# Initialize structured logging
logger = setup_logging(logger_name="api.chat_api")

IDX = "data/index/wp.faiss"
META = "data/index/wp.meta.json"
MODEL = "all-MiniLM-L6-v2"
TOPK_DEFAULT = get_config_value("api.topk_default", 5)
TOPK_MAX = get_config_value("api.topk_max", 10)
TFIDF_VEC = "data/index/wp.tfidf.pkl"
TFIDF_MAT = "data/index/wp.tfidf.npz"

app = FastAPI()


# Exception handler for custom exceptions
@app.exception_handler(WPChatException)
async def wpchat_exception_handler(request: Request, exc: WPChatException):
    """Handle custom WPChat exceptions"""
    return JSONResponse(status_code=get_status_code(exc), content=exc.to_dict())


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add A/B logging middleware
app.middleware("http")(ab_logging_middleware)

# Load global resources
model = SentenceTransformer(MODEL)
index = faiss.read_index(IDX)
meta = json.load(open(META, encoding="utf-8"))
tfidf_vec = joblib.load(TFIDF_VEC) if os.path.exists(TFIDF_VEC) else None
tfidf_mat = load_npz(TFIDF_MAT) if os.path.exists(TFIDF_MAT) else None

# Import and configure chat router (after globals initialized)
from .routers import chat as chat_router  # noqa: E402

chat_router.init_globals(model, index, meta, tfidf_vec, tfidf_mat, TOPK_DEFAULT, TOPK_MAX)
app.include_router(chat_router.router, tags=["Chat"])


# Stats and monitoring endpoints
@app.get("/stats/ab")
def get_ab_statistics(days: int = 7):
    """Get A/B testing statistics"""
    stats = get_ab_stats(days)
    return JSONResponse(stats)


@app.get("/stats/health")
def health_check():
    """Health check endpoint"""
    return JSONResponse(
        {"status": "healthy", "timestamp": datetime.now().isoformat(), "version": "1.0.0"}
    )


@app.get("/stats/highlight")
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
        with open("dashboard.html", encoding="utf-8") as f:
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
        return JSONResponse(
            {"message": f"Canary rollout updated to {percentage:.1%}", "status": "success"}
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/admin/canary/enable")
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


@app.post("/admin/canary/disable")
def disable_canary_endpoint(updated_by: str = "api"):
    """Disable canary deployment"""
    try:
        disable_canary(updated_by)
        return JSONResponse({"message": "Canary deployment disabled", "status": "success"})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/admin/canary/emergency-stop")
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


@app.post("/admin/canary/clear-emergency")
def clear_emergency_stop_endpoint(updated_by: str = "api"):
    """Clear emergency stop"""
    try:
        clear_emergency_stop(updated_by)
        return JSONResponse({"message": "Emergency stop cleared", "status": "success"})
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
        return JSONResponse({"active_incidents": [incident.__dict__ for incident in incidents]})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/admin/incidents/detect")
def detect_incident_endpoint(
    incident_type: str, severity: str, description: str = "", affected_components: list[str] = None
):
    """Manually detect an incident"""
    try:
        incident_type_enum = IncidentType(incident_type)
        severity_enum = Severity(severity)

        incident = detect_incident(
            incident_type=incident_type_enum,
            severity=severity_enum,
            description=description,
            affected_components=affected_components or [],
        )

        return JSONResponse(
            {"message": f"Incident {incident.incident_id} detected", "incident": incident.__dict__}
        )
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

        return JSONResponse(
            {
                "incident_id": incident_id,
                "incident_type": incident.incident_type.value,
                "procedures": [procedure.__dict__ for procedure in procedures],
            }
        )
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

        return JSONResponse({"success": success, "output": output, "action": action.__dict__})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/admin/incidents/{incident_id}/resolve")
def resolve_incident_endpoint(incident_id: str, resolution_notes: str = "", assigned_to: str = ""):
    """Mark an incident as resolved"""
    try:
        success = resolve_incident(incident_id, resolution_notes, assigned_to)

        if success:
            return JSONResponse(
                {"message": f"Incident {incident_id} resolved", "status": "success"}
            )
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

        return JSONResponse(
            {
                "message": f"Detected {len(detected_incidents)} incidents",
                "incidents": [incident.__dict__ for incident in detected_incidents],
            }
        )
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
        return JSONResponse({"backups": [backup.__dict__ for backup in backups]})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/admin/backup/create")
def create_backup_endpoint(backup_type: str = "full", description: str = ""):
    """Create a new backup"""
    try:
        if backup_type not in ["full", "incremental", "index", "cache", "config"]:
            raise HTTPException(400, "Invalid backup type")

        backup = create_backup(backup_type, description)
        return JSONResponse(
            {"message": f"Backup created: {backup.backup_id}", "backup": backup.__dict__}
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/admin/backup/restore")
def restore_backup_endpoint(backup_id: str, target_path: str = None, verify: bool = True):
    """Restore from backup"""
    try:
        restore = restore_backup(backup_id, target_path, verify)
        return JSONResponse(
            {"message": f"Restore completed: {restore.restore_id}", "restore": restore.__dict__}
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.delete("/admin/backup/{backup_id}")
def delete_backup_endpoint(backup_id: str):
    """Delete a backup"""
    try:
        from .backup_manager import backup_manager

        success = backup_manager.delete_backup(backup_id)

        if success:
            return JSONResponse({"message": f"Backup deleted: {backup_id}", "status": "success"})
        else:
            return JSONResponse({"error": "Backup not found"}, status_code=404)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/admin/backup/cleanup")
def cleanup_backups_endpoint():
    """Clean up old backups"""
    try:
        deleted_count = cleanup_old_backups()
        return JSONResponse(
            {"message": f"Cleaned up {deleted_count} old backups", "deleted_count": deleted_count}
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/admin/backup/schedule")
def schedule_backup_endpoint():
    """Schedule automatic backup"""
    try:
        backup = schedule_backup()
        if backup:
            return JSONResponse(
                {
                    "message": f"Scheduled backup created: {backup.backup_id}",
                    "backup": backup.__dict__,
                }
            )
        else:
            return JSONResponse({"message": "No backup needed at this time", "backup": None})
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


# Device status endpoint
@app.get("/stats/device")
def device_status():
    """Get device and model information"""
    device_info = get_device_status()
    return JSONResponse(device_info)
