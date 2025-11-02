#!/usr/bin/env python3
# src/backup_cli.py - Command-line interface for backup management
import argparse
import json
import sys
import time
from typing import Any

import requests


def make_request(method: str, url: str, data: dict[str, Any] = None) -> dict[str, Any]:
    """Make HTTP request to API"""
    try:
        if method.upper() == "GET":
            response = requests.get(url)
        elif method.upper() == "POST":
            response = requests.post(url, json=data)
        elif method.upper() == "DELETE":
            response = requests.delete(url)
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


def get_backup_status(base_url: str = "http://localhost:8080"):
    """Get backup status and statistics"""
    print("💾 Getting backup status...")

    stats = make_request("GET", f"{base_url}/admin/backup/status")

    print("\n📊 Backup Statistics:")
    print(f"   Total Backups: {stats.get('total_backups', 0)}")
    print(f"   Successful: {stats.get('successful_backups', 0)}")
    print(f"   Failed: {stats.get('failed_backups', 0)}")
    print(f"   Success Rate: {stats.get('success_rate', 0):.1%}")
    print(f"   Total Size: {stats.get('total_size_mb', 0):.1f} MB")
    print(f"   Total Files: {stats.get('total_files', 0)}")
    print(f"   Recent Backups (7d): {stats.get('recent_backups_7d', 0)}")

    type_breakdown = stats.get("type_breakdown", {})
    if type_breakdown:
        print("\n📋 Backup Types:")
        for backup_type, count in type_breakdown.items():
            print(f"   {backup_type}: {count}")

    oldest = stats.get("oldest_backup")
    newest = stats.get("newest_backup")
    if oldest:
        print(f"\n📅 Oldest Backup: {time.ctime(oldest)}")
    if newest:
        print(f"📅 Newest Backup: {time.ctime(newest)}")


def list_backups(base_url: str = "http://localhost:8080", backup_type: str = None):
    """List available backups"""
    print("📋 Listing available backups...")

    url = f"{base_url}/admin/backup/list"
    if backup_type:
        url += f"?backup_type={backup_type}"

    response = make_request("GET", url)
    backups = response.get("backups", [])

    if not backups:
        print("✅ No backups found")
        return

    print(f"\n💾 Available Backups ({len(backups)}):")
    for backup in backups:
        status_icon = (
            "✅"
            if backup["status"] == "verified"
            else "❌"
            if backup["status"] == "failed"
            else "⏳"
        )
        print(f"\n{status_icon} {backup['backup_id']}")
        print(f"   Type: {backup['backup_type']}")
        print(f"   Status: {backup['status']}")
        print(f"   Size: {backup['size_bytes'] / (1024*1024):.1f} MB")
        print(f"   Files: {backup['file_count']}")
        print(f"   Created: {time.ctime(backup['created_at'])}")
        if backup.get("description"):
            print(f"   Description: {backup['description']}")


def create_backup(
    backup_type: str = "full", description: str = "", base_url: str = "http://localhost:8080"
):
    """Create a new backup"""
    print(f"💾 Creating {backup_type} backup...")

    data = {"backup_type": backup_type, "description": description}

    result = make_request("POST", f"{base_url}/admin/backup/create", data)

    backup = result.get("backup", {})
    print(f"✅ {result.get('message', 'Backup created')}")
    print(f"   Backup ID: {backup.get('backup_id', 'N/A')}")
    print(f"   Type: {backup.get('backup_type', 'N/A')}")
    print(f"   Status: {backup.get('status', 'N/A')}")
    print(f"   Size: {backup.get('size_bytes', 0) / (1024*1024):.1f} MB")
    print(f"   Files: {backup.get('file_count', 0)}")


def restore_backup(
    backup_id: str,
    target_path: str = None,
    verify: bool = True,
    base_url: str = "http://localhost:8080",
):
    """Restore from backup"""
    print(f"🔄 Restoring backup {backup_id}...")

    if not verify:
        confirm = input("⚠️  Restore without verification? Type 'yes' to confirm: ")
        if confirm.lower() != "yes":
            print("❌ Restore cancelled")
            return

    data = {"backup_id": backup_id, "target_path": target_path, "verify": verify}

    result = make_request("POST", f"{base_url}/admin/backup/restore", data)

    restore = result.get("restore", {})
    print(f"✅ {result.get('message', 'Restore completed')}")
    print(f"   Restore ID: {restore.get('restore_id', 'N/A')}")
    print(f"   Status: {restore.get('status', 'N/A')}")
    print(f"   Verification: {'✅' if restore.get('verification_passed', False) else '❌'}")
    print(f"   Files Restored: {len(restore.get('restored_files', []))}")


def delete_backup(backup_id: str, base_url: str = "http://localhost:8080"):
    """Delete a backup"""
    print(f"🗑️  Deleting backup {backup_id}...")

    confirm = input("⚠️  Are you sure? Type 'yes' to confirm: ")
    if confirm.lower() != "yes":
        print("❌ Delete cancelled")
        return

    result = make_request("DELETE", f"{base_url}/admin/backup/{backup_id}")

    print(f"✅ {result.get('message', 'Backup deleted')}")


def cleanup_backups(base_url: str = "http://localhost:8080"):
    """Clean up old backups"""
    print("🧹 Cleaning up old backups...")

    result = make_request("POST", f"{base_url}/admin/backup/cleanup")

    deleted_count = result.get("deleted_count", 0)
    print(f"✅ {result.get('message', f'Cleaned up {deleted_count} backups')}")


def schedule_backup(base_url: str = "http://localhost:8080"):
    """Schedule automatic backup"""
    print("⏰ Scheduling automatic backup...")

    result = make_request("POST", f"{base_url}/admin/backup/schedule")

    backup = result.get("backup")
    if backup:
        print(f"✅ {result.get('message', 'Scheduled backup created')}")
        print(f"   Backup ID: {backup.get('backup_id', 'N/A')}")
        print(f"   Type: {backup.get('backup_type', 'N/A')}")
    else:
        print(f"ℹ️  {result.get('message', 'No backup needed')}")


def verify_backup(backup_id: str, base_url: str = "http://localhost:8080"):
    """Verify backup integrity"""
    print(f"🔍 Verifying backup {backup_id}...")

    # Get backup info
    response = make_request("GET", f"{base_url}/admin/backup/list")
    backups = response.get("backups", [])

    backup = next((b for b in backups if b["backup_id"] == backup_id), None)
    if not backup:
        print(f"❌ Backup not found: {backup_id}")
        return

    print("📋 Backup Information:")
    print(f"   ID: {backup['backup_id']}")
    print(f"   Type: {backup['backup_type']}")
    print(f"   Status: {backup['status']}")
    print(f"   Checksum: {backup['checksum']}")
    print(f"   Size: {backup['size_bytes'] / (1024*1024):.1f} MB")

    if backup["status"] == "verified":
        print("✅ Backup is verified and ready for restore")
    elif backup["status"] == "failed":
        print("❌ Backup verification failed")
    else:
        print("⏳ Backup verification pending")


def backup_report(base_url: str = "http://localhost:8080"):
    """Generate backup report"""
    print("📊 Generating backup report...")

    stats = make_request("GET", f"{base_url}/admin/backup/status")
    response = make_request("GET", f"{base_url}/admin/backup/list")
    backups = response.get("backups", [])

    print("\n📈 BACKUP REPORT")
    print("=" * 50)

    # Summary
    print("\n📊 Summary:")
    print(f"   Total Backups: {stats.get('total_backups', 0)}")
    print(f"   Success Rate: {stats.get('success_rate', 0):.1%}")
    print(f"   Total Size: {stats.get('total_size_mb', 0):.1f} MB")
    print(f"   Recent Activity: {stats.get('recent_backups_7d', 0)} backups in last 7 days")

    # Recent backups
    recent_backups = sorted(backups, key=lambda b: b["created_at"], reverse=True)[:5]
    if recent_backups:
        print("\n🕒 Recent Backups:")
        for backup in recent_backups:
            status_icon = (
                "✅"
                if backup["status"] == "verified"
                else "❌"
                if backup["status"] == "failed"
                else "⏳"
            )
            print(
                f"   {status_icon} {backup['backup_id']} ({backup['backup_type']}) - {time.ctime(backup['created_at'])}"
            )

    # Recommendations
    print("\n💡 Recommendations:")
    if stats.get("success_rate", 0) < 0.9:
        print("   ⚠️  Low success rate - check backup configuration")
    if stats.get("recent_backups_7d", 0) == 0:
        print("   ⚠️  No recent backups - consider scheduling")
    if stats.get("total_size_mb", 0) > 1000:
        print("   💾 Large backup size - consider cleanup")

    print("   ✅ Regular backups are essential for data protection")
    print("   ✅ Test restore procedures periodically")


def main():
    parser = argparse.ArgumentParser(description="Backup Management CLI")
    parser.add_argument(
        "--base-url", default="http://localhost:8080", help="Base URL of the API server"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Status command
    subparsers.add_parser("status", help="Get backup status and statistics")

    # List command
    list_parser = subparsers.add_parser("list", help="List available backups")
    list_parser.add_argument("--type", help="Filter by backup type")

    # Create command
    create_parser = subparsers.add_parser("create", help="Create a new backup")
    create_parser.add_argument(
        "--type", default="full", help="Backup type (full, incremental, index, cache, config)"
    )
    create_parser.add_argument("--description", default="", help="Backup description")

    # Restore command
    restore_parser = subparsers.add_parser("restore", help="Restore from backup")
    restore_parser.add_argument("backup_id", help="Backup ID to restore")
    restore_parser.add_argument("--target", help="Target path for restore")
    restore_parser.add_argument("--no-verify", action="store_true", help="Skip verification")

    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete a backup")
    delete_parser.add_argument("backup_id", help="Backup ID to delete")

    # Cleanup command
    subparsers.add_parser("cleanup", help="Clean up old backups")

    # Schedule command
    subparsers.add_parser("schedule", help="Schedule automatic backup")

    # Verify command
    verify_parser = subparsers.add_parser("verify", help="Verify backup integrity")
    verify_parser.add_argument("backup_id", help="Backup ID to verify")

    # Report command
    subparsers.add_parser("report", help="Generate backup report")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == "status":
        get_backup_status(args.base_url)
    elif args.command == "list":
        list_backups(args.base_url, args.type)
    elif args.command == "create":
        create_backup(args.type, args.description, args.base_url)
    elif args.command == "restore":
        restore_backup(args.backup_id, args.target, not args.no_verify, args.base_url)
    elif args.command == "delete":
        delete_backup(args.backup_id, args.base_url)
    elif args.command == "cleanup":
        cleanup_backups(args.base_url)
    elif args.command == "schedule":
        schedule_backup(args.base_url)
    elif args.command == "verify":
        verify_backup(args.backup_id, args.base_url)
    elif args.command == "report":
        backup_report(args.base_url)


if __name__ == "__main__":
    main()
