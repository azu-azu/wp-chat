#!/usr/bin/env python3
# src/incident_cli.py - Command-line interface for incident response
import argparse
import sys
import json
import requests
import time
from typing import Dict, Any, List

def make_request(method: str, url: str, data: Dict[str, Any] = None) -> Dict[str, Any]:
    """Make HTTP request to API"""
    try:
        if method.upper() == "GET":
            response = requests.get(url)
        elif method.upper() == "POST":
            response = requests.post(url, json=data)
        else:
            raise ValueError(f"Unsupported method: {method}")

        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ API request failed: {e}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON response: {e}")
        sys.exit(1)

def get_incident_status(base_url: str = "http://localhost:8080"):
    """Get current incident status"""
    print("🚨 Getting incident status...")

    status = make_request("GET", f"{base_url}/admin/incidents/status")

    print(f"\n📊 Incident Status:")
    print(f"   Active Incidents: {status.get('active_incidents', 0)}")
    print(f"   Recent Incidents (24h): {status.get('recent_incidents_24h', 0)}")

    severity_breakdown = status.get('severity_breakdown', {})
    if severity_breakdown:
        print(f"\n🔴 Severity Breakdown:")
        for severity, count in severity_breakdown.items():
            print(f"   {severity.upper()}: {count}")

    type_breakdown = status.get('type_breakdown', {})
    if type_breakdown:
        print(f"\n📋 Incident Types:")
        for incident_type, count in type_breakdown.items():
            print(f"   {incident_type}: {count}")

    active_incidents = status.get('active_incidents_list', [])
    if active_incidents:
        print(f"\n🚨 Active Incidents:")
        for incident in active_incidents:
            print(f"   {incident['incident_id']}: {incident['incident_type']} ({incident['severity']})")
            print(f"      Description: {incident.get('description', 'N/A')}")
            print(f"      Detected: {time.ctime(incident['detected_at'])}")
            print(f"      Components: {', '.join(incident.get('affected_components', []))}")
            print()

def get_active_incidents(base_url: str = "http://localhost:8080"):
    """Get all active incidents"""
    print("🔍 Getting active incidents...")

    response = make_request("GET", f"{base_url}/admin/incidents/active")
    incidents = response.get('active_incidents', [])

    if not incidents:
        print("✅ No active incidents")
        return

    print(f"\n🚨 Active Incidents ({len(incidents)}):")
    for incident in incidents:
        print(f"\n📋 Incident: {incident['incident_id']}")
        print(f"   Type: {incident['incident_type']}")
        print(f"   Severity: {incident['severity']}")
        print(f"   Description: {incident.get('description', 'N/A')}")
        print(f"   Detected: {time.ctime(incident['detected_at'])}")
        print(f"   Components: {', '.join(incident.get('affected_components', []))}")
        print(f"   Actions Taken: {len(incident.get('actions_taken', []))}")

def detect_incident(incident_type: str, severity: str, description: str = "",
                   affected_components: List[str] = None, base_url: str = "http://localhost:8080"):
    """Manually detect an incident"""
    print(f"🚨 Detecting incident: {incident_type} ({severity})")

    data = {
        "incident_type": incident_type,
        "severity": severity,
        "description": description,
        "affected_components": affected_components or []
    }

    result = make_request("POST", f"{base_url}/admin/incidents/detect", data)

    incident = result.get('incident', {})
    print(f"✅ {result.get('message', 'Incident detected')}")
    print(f"   Incident ID: {incident.get('incident_id', 'N/A')}")
    print(f"   Type: {incident.get('incident_type', 'N/A')}")
    print(f"   Severity: {incident.get('severity', 'N/A')}")

def get_procedures(incident_id: str, base_url: str = "http://localhost:8080"):
    """Get emergency procedures for an incident"""
    print(f"📋 Getting procedures for incident {incident_id}...")

    response = make_request("GET", f"{base_url}/admin/incidents/{incident_id}/procedures")

    procedures = response.get('procedures', [])
    incident_type = response.get('incident_type', 'unknown')

    print(f"\n🔧 Emergency Procedures for {incident_type}:")
    for i, procedure in enumerate(procedures, 1):
        print(f"\n{i}. {procedure['name']}")
        print(f"   Description: {procedure['description']}")
        print(f"   Command: {procedure['command']}")
        print(f"   Estimated Time: {procedure['estimated_time']}s")
        print(f"   Requires Confirmation: {'Yes' if procedure['requires_confirmation'] else 'No'}")

def execute_action(incident_id: str, action_id: str, confirm: bool = False,
                  base_url: str = "http://localhost:8080"):
    """Execute an emergency action"""
    print(f"⚡ Executing action {action_id} for incident {incident_id}...")

    if not confirm:
        confirm_input = input("This action requires confirmation. Type 'yes' to proceed: ")
        confirm = confirm_input.lower() == 'yes'

    data = {
        "action_id": action_id,
        "confirm": confirm
    }

    result = make_request("POST", f"{base_url}/admin/incidents/{incident_id}/execute", data)

    if result.get('success', False):
        print(f"✅ Action executed successfully")
        print(f"   Output: {result.get('output', 'N/A')}")
    else:
        print(f"❌ Action failed")
        print(f"   Error: {result.get('output', 'N/A')}")

def resolve_incident(incident_id: str, resolution_notes: str = "", assigned_to: str = "",
                   base_url: str = "http://localhost:8080"):
    """Resolve an incident"""
    print(f"✅ Resolving incident {incident_id}...")

    data = {
        "resolution_notes": resolution_notes,
        "assigned_to": assigned_to
    }

    result = make_request("POST", f"{base_url}/admin/incidents/{incident_id}/resolve", data)

    print(f"✅ {result.get('message', 'Incident resolved')}")

def auto_detect_incidents(base_url: str = "http://localhost:8080"):
    """Automatically detect incidents from SLO status"""
    print("🔍 Auto-detecting incidents from SLO status...")

    result = make_request("POST", f"{base_url}/admin/incidents/auto-detect")

    incidents = result.get('incidents', [])
    print(f"✅ {result.get('message', f'Detected {len(incidents)} incidents')}")

    if incidents:
        print(f"\n🚨 Detected Incidents:")
        for incident in incidents:
            print(f"   {incident['incident_id']}: {incident['incident_type']} ({incident['severity']})")
            print(f"      Description: {incident.get('description', 'N/A')}")

def emergency_procedures():
    """Show emergency procedures reference"""
    print("🚨 EMERGENCY PROCEDURES REFERENCE")
    print("=" * 50)

    procedures = {
        "HIGH_LATENCY": [
            "1. Disable Cross-Encoder Reranking",
            "2. Clear Cache",
            "3. Restart Service"
        ],
        "HIGH_ERROR_RATE": [
            "1. Emergency Stop All Features",
            "2. Check Error Logs",
            "3. Restart Service"
        ],
        "MODEL_FAILURE": [
            "1. Disable Reranking",
            "2. Check Model Files",
            "3. Reload Model"
        ],
        "INDEX_CORRUPTION": [
            "1. Verify Index Integrity",
            "2. Rebuild Index",
            "3. Restore from Backup"
        ],
        "MEMORY_EXHAUSTION": [
            "1. Check Memory Usage",
            "2. Clear Cache",
            "3. Restart Service"
        ],
        "CACHE_FAILURE": [
            "1. Disable Caching",
            "2. Clear Cache",
            "3. Check Cache Directory"
        ],
        "RATE_LIMIT_ATTACK": [
            "1. Check Rate Limit Status",
            "2. Adjust Rate Limits",
            "3. Block Attacker IPs"
        ],
        "CANARY_FAILURE": [
            "1. Emergency Stop Canary",
            "2. Disable Canary",
            "3. Check Canary Status"
        ]
    }

    for incident_type, steps in procedures.items():
        print(f"\n🔴 {incident_type}:")
        for step in steps:
            print(f"   {step}")

    print(f"\n📞 Emergency Contacts:")
    print(f"   On-call Engineer: +1-XXX-XXX-XXXX")
    print(f"   Escalation: +1-XXX-XXX-XXXX")
    print(f"   Slack: #incident-response")

def main():
    parser = argparse.ArgumentParser(description="Incident Response CLI")
    parser.add_argument("--base-url", default="http://localhost:8080",
                       help="Base URL of the API server")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Status command
    subparsers.add_parser("status", help="Get current incident status")

    # Active incidents command
    subparsers.add_parser("active", help="Get all active incidents")

    # Detect incident command
    detect_parser = subparsers.add_parser("detect", help="Manually detect an incident")
    detect_parser.add_argument("incident_type", help="Type of incident")
    detect_parser.add_argument("severity", help="Severity level")
    detect_parser.add_argument("--description", default="", help="Incident description")
    detect_parser.add_argument("--components", nargs="+", help="Affected components")

    # Procedures command
    procedures_parser = subparsers.add_parser("procedures", help="Get emergency procedures")
    procedures_parser.add_argument("incident_id", help="Incident ID")

    # Execute action command
    execute_parser = subparsers.add_parser("execute", help="Execute emergency action")
    execute_parser.add_argument("incident_id", help="Incident ID")
    execute_parser.add_argument("action_id", help="Action ID")
    execute_parser.add_argument("--confirm", action="store_true", help="Skip confirmation")

    # Resolve incident command
    resolve_parser = subparsers.add_parser("resolve", help="Resolve an incident")
    resolve_parser.add_argument("incident_id", help="Incident ID")
    resolve_parser.add_argument("--notes", default="", help="Resolution notes")
    resolve_parser.add_argument("--assigned-to", default="", help="Assigned to")

    # Auto-detect command
    subparsers.add_parser("auto-detect", help="Auto-detect incidents from SLO")

    # Emergency procedures reference
    subparsers.add_parser("emergency-ref", help="Show emergency procedures reference")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == "status":
        get_incident_status(args.base_url)
    elif args.command == "active":
        get_active_incidents(args.base_url)
    elif args.command == "detect":
        detect_incident(args.incident_type, args.severity, args.description,
                       args.components, args.base_url)
    elif args.command == "procedures":
        get_procedures(args.incident_id, args.base_url)
    elif args.command == "execute":
        execute_action(args.incident_id, args.action_id, args.confirm, args.base_url)
    elif args.command == "resolve":
        resolve_incident(args.incident_id, args.notes, args.assigned_to, args.base_url)
    elif args.command == "auto-detect":
        auto_detect_incidents(args.base_url)
    elif args.command == "emergency-ref":
        emergency_procedures()

if __name__ == "__main__":
    main()
