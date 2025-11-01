# src/runbook.py - Incident response runbook and emergency procedures
import json
import logging
import os
import subprocess
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class Severity(Enum):
    """Incident severity levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentType(Enum):
    """Types of incidents"""

    HIGH_LATENCY = "high_latency"
    HIGH_ERROR_RATE = "high_error_rate"
    MODEL_FAILURE = "model_failure"
    INDEX_CORRUPTION = "index_corruption"
    MEMORY_EXHAUSTION = "memory_exhaustion"
    CACHE_FAILURE = "cache_failure"
    RATE_LIMIT_ATTACK = "rate_limit_attack"
    CANARY_FAILURE = "canary_failure"
    UNKNOWN = "unknown"


@dataclass
class Incident:
    """Incident record"""

    incident_id: str
    incident_type: IncidentType
    severity: Severity
    detected_at: float
    resolved_at: float | None = None
    description: str = ""
    affected_components: list[str] = None
    actions_taken: list[str] = None
    resolution_notes: str = ""
    assigned_to: str = ""


@dataclass
class EmergencyAction:
    """Emergency action to take"""

    action_id: str
    name: str
    description: str
    command: str
    parameters: dict[str, Any] = None
    requires_confirmation: bool = False
    estimated_time: int = 0  # seconds


class IncidentResponseRunbook:
    """Incident response runbook and emergency procedures"""

    def __init__(
        self,
        incidents_file: str = "logs/incidents.jsonl",
        runbook_file: str = "logs/runbook_config.json",
    ):
        self.incidents_file = incidents_file
        self.runbook_file = runbook_file
        self.incidents: list[Incident] = []
        self._ensure_logs_dir()
        self._load_incidents()
        self._initialize_runbook()

    def _ensure_logs_dir(self):
        """Ensure logs directory exists"""
        os.makedirs(os.path.dirname(self.incidents_file), exist_ok=True)
        os.makedirs(os.path.dirname(self.runbook_file), exist_ok=True)

    def _load_incidents(self):
        """Load incident history"""
        try:
            if os.path.exists(self.incidents_file):
                with open(self.incidents_file) as f:
                    for line in f:
                        data = json.loads(line.strip())
                        incident = Incident(**data)
                        incident.incident_type = IncidentType(incident.incident_type)
                        incident.severity = Severity(incident.severity)
                        self.incidents.append(incident)
        except Exception as e:
            logger.error(f"Failed to load incidents: {e}")

    def _save_incident(self, incident: Incident):
        """Save incident to file"""
        try:
            incident_dict = asdict(incident)
            # Convert enums to strings for JSON serialization
            incident_dict["incident_type"] = incident.incident_type.value
            incident_dict["severity"] = incident.severity.value
            with open(self.incidents_file, "a") as f:
                f.write(json.dumps(incident_dict) + "\n")
        except Exception as e:
            logger.error(f"Failed to save incident: {e}")

    def _initialize_runbook(self):
        """Initialize emergency runbook procedures"""
        self.emergency_procedures = {
            IncidentType.HIGH_LATENCY: [
                EmergencyAction(
                    action_id="disable_rerank",
                    name="Disable Cross-Encoder Reranking",
                    description="Temporarily disable reranking to reduce latency",
                    command="curl -X POST http://localhost:8080/admin/canary/disable",
                    requires_confirmation=True,
                    estimated_time=30,
                ),
                EmergencyAction(
                    action_id="clear_cache",
                    name="Clear Cache",
                    description="Clear all cached data to free up resources",
                    command="curl -X POST http://localhost:8080/admin/cache/clear",
                    requires_confirmation=True,
                    estimated_time=60,
                ),
                EmergencyAction(
                    action_id="restart_service",
                    name="Restart Service",
                    description="Restart the API service to clear memory issues",
                    command="pkill -f uvicorn && sleep 5 && uvicorn src.chat_api:app --host 0.0.0.0 --port 8080 --reload &",
                    requires_confirmation=True,
                    estimated_time=120,
                ),
            ],
            IncidentType.HIGH_ERROR_RATE: [
                EmergencyAction(
                    action_id="emergency_stop",
                    name="Emergency Stop All Features",
                    description="Immediately disable all advanced features",
                    command="curl -X POST http://localhost:8080/admin/canary/emergency-stop",
                    requires_confirmation=True,
                    estimated_time=30,
                ),
                EmergencyAction(
                    action_id="check_logs",
                    name="Check Error Logs",
                    description="Examine recent error logs for root cause",
                    command="tail -n 100 logs/api_errors.log",
                    requires_confirmation=False,
                    estimated_time=60,
                ),
                EmergencyAction(
                    action_id="restart_service",
                    name="Restart Service",
                    description="Restart the API service",
                    command="pkill -f uvicorn && sleep 5 && uvicorn src.chat_api:app --host 0.0.0.0 --port 8080 --reload &",
                    requires_confirmation=True,
                    estimated_time=120,
                ),
            ],
            IncidentType.MODEL_FAILURE: [
                EmergencyAction(
                    action_id="disable_rerank",
                    name="Disable Reranking",
                    description="Disable Cross-Encoder reranking",
                    command="curl -X POST http://localhost:8080/admin/canary/disable",
                    requires_confirmation=True,
                    estimated_time=30,
                ),
                EmergencyAction(
                    action_id="check_model_files",
                    name="Check Model Files",
                    description="Verify model files are accessible",
                    command="ls -la ~/.cache/huggingface/transformers/",
                    requires_confirmation=False,
                    estimated_time=30,
                ),
                EmergencyAction(
                    action_id="reload_model",
                    name="Reload Model",
                    description="Restart service to reload models",
                    command="pkill -f uvicorn && sleep 5 && uvicorn src.chat_api:app --host 0.0.0.0 --port 8080 --reload &",
                    requires_confirmation=True,
                    estimated_time=180,
                ),
            ],
            IncidentType.INDEX_CORRUPTION: [
                EmergencyAction(
                    action_id="verify_index",
                    name="Verify Index Integrity",
                    description="Check if index files are corrupted",
                    command="python -c \"import faiss; idx = faiss.read_index('data/index/wp.faiss'); print(f'Index size: {idx.ntotal}')\"",
                    requires_confirmation=False,
                    estimated_time=60,
                ),
                EmergencyAction(
                    action_id="rebuild_index",
                    name="Rebuild Index",
                    description="Rebuild the search index from clean data",
                    command="make rebuild-index",
                    requires_confirmation=True,
                    estimated_time=1800,
                ),
                EmergencyAction(
                    action_id="restore_backup",
                    name="Restore from Backup",
                    description="Restore index from latest backup",
                    command="cp data/index/wp.faiss.backup data/index/wp.faiss",
                    requires_confirmation=True,
                    estimated_time=300,
                ),
            ],
            IncidentType.MEMORY_EXHAUSTION: [
                EmergencyAction(
                    action_id="check_memory",
                    name="Check Memory Usage",
                    description="Check current memory usage",
                    command="free -h && ps aux --sort=-%mem | head -10",
                    requires_confirmation=False,
                    estimated_time=30,
                ),
                EmergencyAction(
                    action_id="clear_cache",
                    name="Clear Cache",
                    description="Clear all cached data",
                    command="curl -X POST http://localhost:8080/admin/cache/clear",
                    requires_confirmation=True,
                    estimated_time=60,
                ),
                EmergencyAction(
                    action_id="restart_service",
                    name="Restart Service",
                    description="Restart service to free memory",
                    command="pkill -f uvicorn && sleep 5 && uvicorn src.chat_api:app --host 0.0.0.0 --port 8080 --reload &",
                    requires_confirmation=True,
                    estimated_time=120,
                ),
            ],
            IncidentType.CACHE_FAILURE: [
                EmergencyAction(
                    action_id="disable_cache",
                    name="Disable Caching",
                    description="Temporarily disable caching",
                    command="curl -X POST http://localhost:8080/admin/cache/disable",
                    requires_confirmation=True,
                    estimated_time=30,
                ),
                EmergencyAction(
                    action_id="clear_cache",
                    name="Clear Cache",
                    description="Clear all cached data",
                    command="curl -X POST http://localhost:8080/admin/cache/clear",
                    requires_confirmation=True,
                    estimated_time=60,
                ),
                EmergencyAction(
                    action_id="check_cache_dir",
                    name="Check Cache Directory",
                    description="Check cache directory permissions and space",
                    command="ls -la logs/cache/ && df -h logs/cache/",
                    requires_confirmation=False,
                    estimated_time=30,
                ),
            ],
            IncidentType.RATE_LIMIT_ATTACK: [
                EmergencyAction(
                    action_id="check_rate_limits",
                    name="Check Rate Limit Status",
                    description="Check current rate limiting status",
                    command="curl http://localhost:8080/stats/rate-limit",
                    requires_confirmation=False,
                    estimated_time=30,
                ),
                EmergencyAction(
                    action_id="adjust_rate_limits",
                    name="Adjust Rate Limits",
                    description="Temporarily lower rate limits",
                    command='curl -X POST http://localhost:8080/admin/rate-limit/adjust -d \'{"max_requests": 10, "window_seconds": 3600}\'',
                    requires_confirmation=True,
                    estimated_time=60,
                ),
                EmergencyAction(
                    action_id="block_attacker",
                    name="Block Attacker IPs",
                    description="Block suspicious IP addresses",
                    command="iptables -A INPUT -s <ATTACKER_IP> -j DROP",
                    requires_confirmation=True,
                    estimated_time=120,
                ),
            ],
            IncidentType.CANARY_FAILURE: [
                EmergencyAction(
                    action_id="emergency_stop_canary",
                    name="Emergency Stop Canary",
                    description="Immediately stop canary deployment",
                    command="curl -X POST http://localhost:8080/admin/canary/emergency-stop",
                    requires_confirmation=True,
                    estimated_time=30,
                ),
                EmergencyAction(
                    action_id="disable_canary",
                    name="Disable Canary",
                    description="Disable canary deployment",
                    command="curl -X POST http://localhost:8080/admin/canary/disable",
                    requires_confirmation=True,
                    estimated_time=30,
                ),
                EmergencyAction(
                    action_id="check_canary_status",
                    name="Check Canary Status",
                    description="Check current canary deployment status",
                    command="curl http://localhost:8080/admin/canary/status",
                    requires_confirmation=False,
                    estimated_time=30,
                ),
            ],
        }

    def detect_incident(
        self,
        incident_type: IncidentType,
        severity: Severity,
        description: str = "",
        affected_components: list[str] = None,
    ) -> Incident:
        """Detect and record a new incident"""
        incident_id = f"incident_{int(time.time())}"
        incident = Incident(
            incident_id=incident_id,
            incident_type=incident_type,
            severity=severity,
            detected_at=time.time(),
            description=description,
            affected_components=affected_components or [],
            actions_taken=[],
        )

        self.incidents.append(incident)
        self._save_incident(incident)

        logger.warning(
            f"🚨 INCIDENT DETECTED: {incident_id} - {incident_type.value} ({severity.value})"
        )
        return incident

    def get_emergency_procedures(self, incident_type: IncidentType) -> list[EmergencyAction]:
        """Get emergency procedures for incident type"""
        return self.emergency_procedures.get(incident_type, [])

    def execute_emergency_action(
        self, action: EmergencyAction, incident: Incident, confirm: bool = False
    ) -> tuple[bool, str]:
        """Execute an emergency action"""
        if action.requires_confirmation and not confirm:
            return False, "Action requires confirmation"

        try:
            logger.info(f"Executing emergency action: {action.name}")

            # Record action in incident
            incident.actions_taken.append(f"{datetime.now().isoformat()}: {action.name}")

            # Execute command
            if action.command.startswith("curl"):
                # HTTP request
                result = subprocess.run(
                    action.command,
                    shell=False,
                    capture_output=True,
                    text=True,
                    timeout=action.estimated_time,
                )
                if result.returncode == 0:
                    return True, result.stdout
                else:
                    return False, result.stderr
            else:
                # System command
                result = subprocess.run(
                    action.command,
                    shell=False,
                    capture_output=True,
                    text=True,
                    timeout=action.estimated_time,
                )
                if result.returncode == 0:
                    return True, result.stdout
                else:
                    return False, result.stderr

        except subprocess.TimeoutExpired:
            return False, f"Action timed out after {action.estimated_time} seconds"
        except Exception as e:
            return False, str(e)

    def resolve_incident(self, incident_id: str, resolution_notes: str = "", assigned_to: str = ""):
        """Mark incident as resolved"""
        for incident in self.incidents:
            if incident.incident_id == incident_id:
                incident.resolved_at = time.time()
                incident.resolution_notes = resolution_notes
                incident.assigned_to = assigned_to

                # Update saved incident
                self._save_incident(incident)

                logger.info(f"✅ INCIDENT RESOLVED: {incident_id}")
                return True
        return False

    def get_active_incidents(self) -> list[Incident]:
        """Get all active (unresolved) incidents"""
        return [inc for inc in self.incidents if inc.resolved_at is None]

    def get_incident_history(self, hours: int = 24) -> list[Incident]:
        """Get incident history for the last N hours"""
        cutoff_time = time.time() - (hours * 3600)
        return [inc for inc in self.incidents if inc.detected_at >= cutoff_time]

    def get_incident_summary(self) -> dict[str, Any]:
        """Get incident summary statistics"""
        active_incidents = self.get_active_incidents()
        recent_incidents = self.get_incident_history(24)

        # Count by severity
        severity_counts = {}
        for incident in recent_incidents:
            severity = incident.severity.value
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

        # Count by type
        type_counts = {}
        for incident in recent_incidents:
            incident_type = incident.incident_type.value
            type_counts[incident_type] = type_counts.get(incident_type, 0) + 1

        return {
            "active_incidents": len(active_incidents),
            "recent_incidents_24h": len(recent_incidents),
            "severity_breakdown": severity_counts,
            "type_breakdown": type_counts,
            "active_incidents_list": [asdict(inc) for inc in active_incidents],
            "recent_incidents_list": [asdict(inc) for inc in recent_incidents[-10:]],  # Last 10
        }

    def auto_detect_incidents(self, slo_status: dict[str, Any]) -> list[Incident]:
        """Automatically detect incidents from SLO status"""
        detected_incidents = []

        for endpoint, status in slo_status.items():
            if not isinstance(status, dict) or "violations" not in status:
                continue

            violations = status.get("violations", [])
            if not violations:
                continue

            # Determine incident type and severity
            incident_type = IncidentType.UNKNOWN
            severity = Severity.MEDIUM

            for violation in violations:
                violation_type = violation.get("type", "")

                if "latency" in violation_type.lower():
                    incident_type = IncidentType.HIGH_LATENCY
                    severity = Severity.HIGH
                elif (
                    "success_rate" in violation_type.lower()
                    or "error_rate" in violation_type.lower()
                ):
                    incident_type = IncidentType.HIGH_ERROR_RATE
                    severity = Severity.CRITICAL
                elif "fallback" in violation_type.lower():
                    incident_type = IncidentType.MODEL_FAILURE
                    severity = Severity.HIGH

            if incident_type != IncidentType.UNKNOWN:
                description = f"SLO violations detected for {endpoint}: " + "; ".join(
                    [v.get("message", "") for v in violations]
                )
                incident = self.detect_incident(
                    incident_type=incident_type,
                    severity=severity,
                    description=description,
                    affected_components=[endpoint],
                )
                detected_incidents.append(incident)

        return detected_incidents


# Global runbook instance
runbook = IncidentResponseRunbook()


def detect_incident(
    incident_type: IncidentType,
    severity: Severity,
    description: str = "",
    affected_components: list[str] = None,
) -> Incident:
    """Detect and record a new incident"""
    return runbook.detect_incident(incident_type, severity, description, affected_components)


def get_emergency_procedures(incident_type: IncidentType) -> list[EmergencyAction]:
    """Get emergency procedures for incident type"""
    return runbook.get_emergency_procedures(incident_type)


def execute_emergency_action(
    action: EmergencyAction, incident: Incident, confirm: bool = False
) -> tuple[bool, str]:
    """Execute an emergency action"""
    return runbook.execute_emergency_action(action, incident, confirm)


def resolve_incident(incident_id: str, resolution_notes: str = "", assigned_to: str = ""):
    """Mark incident as resolved"""
    return runbook.resolve_incident(incident_id, resolution_notes, assigned_to)


def get_active_incidents() -> list[Incident]:
    """Get all active incidents"""
    return runbook.get_active_incidents()


def get_incident_summary() -> dict[str, Any]:
    """Get incident summary"""
    return runbook.get_incident_summary()


def auto_detect_incidents(slo_status: dict[str, Any]) -> list[Incident]:
    """Automatically detect incidents from SLO status"""
    return runbook.auto_detect_incidents(slo_status)
