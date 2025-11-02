"""Admin Backup router - handles /admin/backup/* endpoints"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

# Import backup management functions
from ...management.backup_manager import (
    cleanup_old_backups,
    create_backup,
    get_backup_statistics,
    list_backups,
    restore_backup,
    schedule_backup,
)

router = APIRouter()


@router.get("/status")
def get_backup_status():
    """Get backup status and statistics"""
    try:
        stats = get_backup_statistics()
        return JSONResponse(stats)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/list")
def list_backups_endpoint(backup_type: str = None):
    """List available backups"""
    try:
        backups = list_backups(backup_type)
        return JSONResponse({"backups": [backup.__dict__ for backup in backups]})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/create")
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


@router.post("/restore")
def restore_backup_endpoint(backup_id: str, target_path: str = None, verify: bool = True):
    """Restore from backup"""
    try:
        restore = restore_backup(backup_id, target_path, verify)
        return JSONResponse(
            {"message": f"Restore completed: {restore.restore_id}", "restore": restore.__dict__}
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.delete("/{backup_id}")
def delete_backup_endpoint(backup_id: str):
    """Delete a backup"""
    try:
        from ...management.backup_manager import backup_manager

        success = backup_manager.delete_backup(backup_id)

        if success:
            return JSONResponse({"message": f"Backup deleted: {backup_id}", "status": "success"})
        else:
            return JSONResponse({"error": "Backup not found"}, status_code=404)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/cleanup")
def cleanup_backups_endpoint():
    """Clean up old backups"""
    try:
        deleted_count = cleanup_old_backups()
        return JSONResponse(
            {"message": f"Cleaned up {deleted_count} old backups", "deleted_count": deleted_count}
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/schedule")
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
