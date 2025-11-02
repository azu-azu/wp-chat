"""Admin Incidents router - handles /admin/incidents/* endpoints"""
from fastapi import APIRouter
from fastapi.responses import JSONResponse

# Import runbook functions
from ...core.runbook import (
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
from ...core.slo_monitoring import get_slo_status

router = APIRouter()


@router.get("/status")
def get_incident_status():
    """Get current incident status and summary"""
    try:
        summary = get_incident_summary()
        return JSONResponse(summary)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/active")
def get_active_incidents_endpoint():
    """Get all active incidents"""
    try:
        incidents = get_active_incidents()
        return JSONResponse({"active_incidents": [incident.__dict__ for incident in incidents]})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/detect")
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


@router.get("/{incident_id}/procedures")
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


@router.post("/{incident_id}/execute")
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


@router.post("/{incident_id}/resolve")
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


@router.post("/auto-detect")
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
