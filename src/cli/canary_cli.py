#!/usr/bin/env python3
# src/canary_cli.py - Command-line interface for canary deployment management
import argparse
import sys
import json
import requests
import time
from typing import Dict, Any

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

def get_status(base_url: str = "http://localhost:8080"):
    """Get current canary deployment status"""
    print("🔍 Getting canary deployment status...")

    status = make_request("GET", f"{base_url}/admin/canary/status")

    config = status.get("config", {})
    summary = status.get("summary", {})

    print(f"\n📊 Canary Deployment Status:")
    print(f"   Status: {status.get('status', 'unknown')}")
    print(f"   Enabled: {config.get('enabled', False)}")
    print(f"   Rollout: {config.get('rollout_percentage', 0.0):.1%}")
    print(f"   Emergency Stop: {config.get('emergency_stop', False)}")
    print(f"   Last Updated: {time.ctime(config.get('last_updated', 0))}")
    print(f"   Updated By: {config.get('updated_by', 'unknown')}")

    if summary and not summary.get("message"):
        print(f"\n📈 Recent Performance:")
        print(f"   Total Requests: {summary.get('total_requests', 0)}")
        print(f"   Rerank Enabled: {summary.get('rerank_enabled_requests', 0)}")
        print(f"   Rerank Disabled: {summary.get('rerank_disabled_requests', 0)}")
        print(f"   Avg Latency (Enabled): {summary.get('avg_latency_enabled', 0):.1f}ms")
        print(f"   Avg Latency (Disabled): {summary.get('avg_latency_disabled', 0):.1f}ms")
        print(f"   Error Rate (Enabled): {summary.get('avg_error_rate_enabled', 0):.3f}")
        print(f"   Error Rate (Disabled): {summary.get('avg_error_rate_disabled', 0):.3f}")

        perf_impact = summary.get('performance_impact', {})
        if perf_impact:
            print(f"\n⚡ Performance Impact:")
            print(f"   Latency Change: {perf_impact.get('latency_change_pct', 0):+.1f}%")
            print(f"   Error Rate Change: {perf_impact.get('error_rate_change_pct', 0):+.1f}%")

def enable_canary(percentage: float, base_url: str = "http://localhost:8080"):
    """Enable canary deployment"""
    print(f"🚀 Enabling canary deployment at {percentage:.1%}...")

    result = make_request("POST", f"{base_url}/admin/canary/enable", {
        "percentage": percentage,
        "updated_by": "cli"
    })

    print(f"✅ {result.get('message', 'Canary deployment enabled')}")

def disable_canary(base_url: str = "http://localhost:8080"):
    """Disable canary deployment"""
    print("🛑 Disabling canary deployment...")

    result = make_request("POST", f"{base_url}/admin/canary/disable", {
        "updated_by": "cli"
    })

    print(f"✅ {result.get('message', 'Canary deployment disabled')}")

def update_rollout(percentage: float, base_url: str = "http://localhost:8080"):
    """Update rollout percentage"""
    print(f"📊 Updating rollout percentage to {percentage:.1%}...")

    result = make_request("POST", f"{base_url}/admin/canary/rollout", {
        "percentage": percentage,
        "updated_by": "cli"
    })

    print(f"✅ {result.get('message', 'Rollout percentage updated')}")

def emergency_stop(base_url: str = "http://localhost:8080"):
    """Emergency stop canary deployment"""
    print("🚨 EMERGENCY STOP - Disabling rerank for all users...")

    confirm = input("Are you sure? Type 'yes' to confirm: ")
    if confirm.lower() != 'yes':
        print("❌ Emergency stop cancelled")
        return

    result = make_request("POST", f"{base_url}/admin/canary/emergency-stop", {
        "updated_by": "cli"
    })

    print(f"✅ {result.get('message', 'Emergency stop activated')}")

def clear_emergency(base_url: str = "http://localhost:8080"):
    """Clear emergency stop"""
    print("🔄 Clearing emergency stop...")

    result = make_request("POST", f"{base_url}/admin/canary/clear-emergency", {
        "updated_by": "cli"
    })

    print(f"✅ {result.get('message', 'Emergency stop cleared')}")

def test_user_assignment(user_ids: list, base_url: str = "http://localhost:8080"):
    """Test user assignment for canary deployment"""
    print("🧪 Testing user assignment...")

    for user_id in user_ids:
        try:
            response = requests.get(f"{base_url}/search", params={
                "q": "test query",
                "user_id": user_id,
                "topk": 1
            })
            response.raise_for_status()
            data = response.json()
            canary_info = data.get("canary", {})
            rerank_enabled = canary_info.get("rerank_enabled", False)
            rollout_pct = canary_info.get("rollout_percentage", 0.0)

            print(f"   User {user_id}: Rerank {'✅' if rerank_enabled else '❌'} (Rollout: {rollout_pct:.1%})")
        except Exception as e:
            print(f"   User {user_id}: ❌ Error - {e}")

def main():
    parser = argparse.ArgumentParser(description="Canary Deployment Management CLI")
    parser.add_argument("--base-url", default="http://localhost:8080",
                       help="Base URL of the API server")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Status command
    subparsers.add_parser("status", help="Get current canary deployment status")

    # Enable command
    enable_parser = subparsers.add_parser("enable", help="Enable canary deployment")
    enable_parser.add_argument("percentage", type=float,
                              help="Rollout percentage (0.0 to 1.0)")

    # Disable command
    subparsers.add_parser("disable", help="Disable canary deployment")

    # Update command
    update_parser = subparsers.add_parser("update", help="Update rollout percentage")
    update_parser.add_argument("percentage", type=float,
                              help="Rollout percentage (0.0 to 1.0)")

    # Emergency stop command
    subparsers.add_parser("emergency-stop", help="Emergency stop canary deployment")

    # Clear emergency command
    subparsers.add_parser("clear-emergency", help="Clear emergency stop")

    # Test command
    test_parser = subparsers.add_parser("test", help="Test user assignment")
    test_parser.add_argument("user_ids", nargs="+",
                            help="User IDs to test")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == "status":
        get_status(args.base_url)
    elif args.command == "enable":
        enable_canary(args.percentage, args.base_url)
    elif args.command == "disable":
        disable_canary(args.base_url)
    elif args.command == "update":
        update_rollout(args.percentage, args.base_url)
    elif args.command == "emergency-stop":
        emergency_stop(args.base_url)
    elif args.command == "clear-emergency":
        clear_emergency(args.base_url)
    elif args.command == "test":
        test_user_assignment(args.user_ids, args.base_url)

if __name__ == "__main__":
    main()
