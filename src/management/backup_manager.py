# src/backup_manager.py - Backup and restore management system
import os
import shutil
import json
import time
import hashlib
import gzip
import tarfile
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
import logging
import subprocess

logger = logging.getLogger(__name__)

@dataclass
class BackupInfo:
    """Backup information record"""
    backup_id: str
    backup_type: str  # 'full', 'incremental', 'index', 'cache', 'config'
    created_at: float
    size_bytes: int
    file_count: int
    checksum: str
    status: str  # 'created', 'verified', 'failed', 'expired'
    description: str = ""
    files: List[str] = None
    metadata: Dict[str, Any] = None

@dataclass
class RestoreInfo:
    """Restore operation record"""
    restore_id: str
    backup_id: str
    restored_at: float
    status: str  # 'success', 'failed', 'partial'
    restored_files: List[str] = None
    error_message: str = ""
    verification_passed: bool = False

class BackupManager:
    """Manages backup and restore operations"""

    def __init__(self, backup_dir: str = "backups",
                 config_file: str = "logs/backup_config.json",
                 history_file: str = "logs/backup_history.jsonl"):
        self.backup_dir = backup_dir
        self.config_file = config_file
        self.history_file = history_file
        self.backups: List[BackupInfo] = []
        self.restores: List[RestoreInfo] = []

        # Backup configuration
        self.config = {
            "enabled": True,
            "schedule": {
                "full_backup_days": 7,  # Full backup every 7 days
                "incremental_hours": 24,  # Incremental backup every 24 hours
                "retention_days": 30,  # Keep backups for 30 days
                "max_backups": 10  # Maximum number of backups to keep
            },
            "paths": {
                "index": "data/index/",
                "cache": "logs/cache/",
                "config": "config.yml",
                "logs": "logs/"
            },
            "compression": True,
            "verification": True,
            "auto_cleanup": True
        }

        self._ensure_directories()
        self._load_config()
        self._load_history()

    def _ensure_directories(self):
        """Ensure backup directories exist"""
        os.makedirs(self.backup_dir, exist_ok=True)
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        os.makedirs(os.path.dirname(self.history_file), exist_ok=True)

    def _load_config(self):
        """Load backup configuration"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    saved_config = json.load(f)
                    self.config.update(saved_config)
            else:
                self._save_config()
        except Exception as e:
            logger.error(f"Failed to load backup config: {e}")

    def _save_config(self):
        """Save backup configuration"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save backup config: {e}")

    def _load_history(self):
        """Load backup history"""
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r') as f:
                    for line in f:
                        data = json.loads(line.strip())
                        if data.get('type') == 'backup':
                            backup = BackupInfo(**data)
                            self.backups.append(backup)
                        elif data.get('type') == 'restore':
                            restore = RestoreInfo(**data)
                            self.restores.append(restore)
        except Exception as e:
            logger.error(f"Failed to load backup history: {e}")

    def _save_backup_record(self, backup: BackupInfo):
        """Save backup record to history"""
        try:
            record = {
                "type": "backup",
                **asdict(backup)
            }
            with open(self.history_file, 'a') as f:
                f.write(json.dumps(record) + '\n')
        except Exception as e:
            logger.error(f"Failed to save backup record: {e}")

    def _save_restore_record(self, restore: RestoreInfo):
        """Save restore record to history"""
        try:
            record = {
                "type": "restore",
                **asdict(restore)
            }
            with open(self.history_file, 'a') as f:
                f.write(json.dumps(record) + '\n')
        except Exception as e:
            logger.error(f"Failed to save restore record: {e}")

    def _calculate_checksum(self, file_path: str) -> str:
        """Calculate MD5 checksum of a file"""
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            logger.error(f"Failed to calculate checksum for {file_path}: {e}")
            return ""

    def _get_file_size(self, file_path: str) -> int:
        """Get file size in bytes"""
        try:
            return os.path.getsize(file_path)
        except Exception:
            return 0

    def create_backup(self, backup_type: str = "full", description: str = "") -> BackupInfo:
        """Create a backup"""
        backup_id = f"backup_{int(time.time())}"
        backup_path = os.path.join(self.backup_dir, f"{backup_id}.tar.gz")

        logger.info(f"Creating {backup_type} backup: {backup_id}")

        try:
            # Collect files to backup
            files_to_backup = []
            total_size = 0

            if backup_type in ["full", "index"]:
                index_path = self.config["paths"]["index"]
                if os.path.exists(index_path):
                    for root, dirs, files in os.walk(index_path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            files_to_backup.append(file_path)
                            total_size += self._get_file_size(file_path)

            if backup_type in ["full", "cache"]:
                cache_path = self.config["paths"]["cache"]
                if os.path.exists(cache_path):
                    for root, dirs, files in os.walk(cache_path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            files_to_backup.append(file_path)
                            total_size += self._get_file_size(file_path)

            if backup_type in ["full", "config"]:
                config_path = self.config["paths"]["config"]
                if os.path.exists(config_path):
                    files_to_backup.append(config_path)
                    total_size += self._get_file_size(config_path)

            if backup_type == "full":
                logs_path = self.config["paths"]["logs"]
                if os.path.exists(logs_path):
                    for root, dirs, files in os.walk(logs_path):
                        for file in files:
                            if not file.endswith('.jsonl'):  # Skip large log files
                                continue
                            file_path = os.path.join(root, file)
                            files_to_backup.append(file_path)
                            total_size += self._get_file_size(file_path)

            if not files_to_backup:
                raise Exception("No files found to backup")

            # Create compressed archive
            with tarfile.open(backup_path, "w:gz") as tar:
                for file_path in files_to_backup:
                    if os.path.exists(file_path):
                        arcname = os.path.relpath(file_path, os.path.dirname(file_path))
                        tar.add(file_path, arcname=arcname)

            # Calculate checksum
            checksum = self._calculate_checksum(backup_path)

            # Create backup record
            backup = BackupInfo(
                backup_id=backup_id,
                backup_type=backup_type,
                created_at=time.time(),
                size_bytes=total_size,
                file_count=len(files_to_backup),
                checksum=checksum,
                status="created",
                description=description,
                files=files_to_backup,
                metadata={
                    "backup_path": backup_path,
                    "compression": self.config["compression"]
                }
            )

            # Verify backup if enabled
            if self.config["verification"]:
                if self._verify_backup(backup):
                    backup.status = "verified"
                else:
                    backup.status = "failed"
                    logger.error(f"Backup verification failed: {backup_id}")

            self.backups.append(backup)
            self._save_backup_record(backup)

            logger.info(f"Backup created successfully: {backup_id} ({total_size} bytes)")
            return backup

        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            # Create failed backup record
            backup = BackupInfo(
                backup_id=backup_id,
                backup_type=backup_type,
                created_at=time.time(),
                size_bytes=0,
                file_count=0,
                checksum="",
                status="failed",
                description=f"Failed: {str(e)}"
            )
            self.backups.append(backup)
            self._save_backup_record(backup)
            raise

    def _verify_backup(self, backup: BackupInfo) -> bool:
        """Verify backup integrity"""
        try:
            backup_path = backup.metadata.get("backup_path")
            if not backup_path or not os.path.exists(backup_path):
                return False

            # Check file size
            actual_size = os.path.getsize(backup_path)
            if actual_size == 0:
                return False

            # Check checksum
            actual_checksum = self._calculate_checksum(backup_path)
            if actual_checksum != backup.checksum:
                logger.error(f"Checksum mismatch for backup {backup.backup_id}")
                return False

            # Test archive integrity
            try:
                with tarfile.open(backup_path, "r:gz") as tar:
                    tar.getmembers()  # This will raise an exception if corrupted
                return True
            except Exception as e:
                logger.error(f"Archive integrity check failed: {e}")
                return False

        except Exception as e:
            logger.error(f"Backup verification error: {e}")
            return False

    def restore_backup(self, backup_id: str, target_path: str = None,
                      verify: bool = True) -> RestoreInfo:
        """Restore from backup"""
        restore_id = f"restore_{int(time.time())}"

        # Find backup
        backup = next((b for b in self.backups if b.backup_id == backup_id), None)
        if not backup:
            raise Exception(f"Backup not found: {backup_id}")

        if backup.status != "verified":
            raise Exception(f"Backup not verified: {backup_id}")

        logger.info(f"Restoring backup: {backup_id}")

        try:
            backup_path = backup.metadata.get("backup_path")
            if not backup_path or not os.path.exists(backup_path):
                raise Exception("Backup file not found")

            # Determine target path
            if not target_path:
                target_path = os.path.dirname(backup.files[0]) if backup.files else "."

            # Create restore record
            restore = RestoreInfo(
                restore_id=restore_id,
                backup_id=backup_id,
                restored_at=time.time(),
                status="success",
                restored_files=[],
                verification_passed=False
            )

            # Extract archive with security check
            with tarfile.open(backup_path, "r:gz") as tar:
                # Check for path traversal vulnerabilities and extract safely
                safe_members = []
                for member in tar.getmembers():
                    if os.path.isabs(member.name) or ".." in member.name:
                        logger.error(f"Unsafe path in archive: {member.name}")
                        raise ValueError(f"Unsafe path detected: {member.name}")

                    # Normalize path to prevent traversal
                    member.name = os.path.normpath(member.name)
                    if member.name.startswith('/') or '..' in member.name:
                        logger.error(f"Normalized unsafe path: {member.name}")
                        raise ValueError(f"Unsafe path detected after normalization: {member.name}")

                    safe_members.append(member)

                # Extract only safe members
                tar.extractall(path=target_path, members=safe_members)
                restore.restored_files = [member.name for member in safe_members]

            # Verify restore if requested
            if verify:
                restore.verification_passed = self._verify_restore(restore, target_path)
                if not restore.verification_passed:
                    restore.status = "partial"
                    logger.warning(f"Restore verification failed: {restore_id}")

            self.restores.append(restore)
            self._save_restore_record(restore)

            logger.info(f"Restore completed: {restore_id}")
            return restore

        except Exception as e:
            logger.error(f"Failed to restore backup: {e}")
            restore = RestoreInfo(
                restore_id=restore_id,
                backup_id=backup_id,
                restored_at=time.time(),
                status="failed",
                error_message=str(e),
                verification_passed=False
            )
            self.restores.append(restore)
            self._save_restore_record(restore)
            raise

    def _verify_restore(self, restore: RestoreInfo, target_path: str) -> bool:
        """Verify restore integrity"""
        try:
            for file_name in restore.restored_files:
                file_path = os.path.join(target_path, file_name)
                if not os.path.exists(file_path):
                    logger.error(f"Restored file not found: {file_path}")
                    return False

                # Check if file is readable
                try:
                    with open(file_path, 'rb') as f:
                        f.read(1)
                except Exception as e:
                    logger.error(f"Cannot read restored file {file_path}: {e}")
                    return False

            return True

        except Exception as e:
            logger.error(f"Restore verification error: {e}")
            return False

    def list_backups(self, backup_type: str = None) -> List[BackupInfo]:
        """List available backups"""
        if backup_type:
            return [b for b in self.backups if b.backup_type == backup_type]
        return self.backups.copy()

    def get_backup_info(self, backup_id: str) -> Optional[BackupInfo]:
        """Get backup information"""
        return next((b for b in self.backups if b.backup_id == backup_id), None)

    def delete_backup(self, backup_id: str) -> bool:
        """Delete backup"""
        backup = self.get_backup_info(backup_id)
        if not backup:
            return False

        try:
            # Delete backup file
            backup_path = backup.metadata.get("backup_path")
            if backup_path and os.path.exists(backup_path):
                os.remove(backup_path)

            # Remove from list
            self.backups.remove(backup)

            # Update status
            backup.status = "expired"
            self._save_backup_record(backup)

            logger.info(f"Backup deleted: {backup_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete backup: {e}")
            return False

    def cleanup_old_backups(self) -> int:
        """Clean up old backups based on retention policy"""
        if not self.config["auto_cleanup"]:
            return 0

        retention_days = self.config["schedule"]["retention_days"]
        max_backups = self.config["schedule"]["max_backups"]
        cutoff_time = time.time() - (retention_days * 24 * 3600)

        deleted_count = 0

        # Sort backups by creation time (oldest first)
        sorted_backups = sorted(self.backups, key=lambda b: b.created_at)

        for backup in sorted_backups:
            should_delete = False

            # Delete if older than retention period
            if backup.created_at < cutoff_time:
                should_delete = True

            # Delete if we have too many backups
            elif len(self.backups) > max_backups:
                should_delete = True

            if should_delete:
                if self.delete_backup(backup.backup_id):
                    deleted_count += 1

        logger.info(f"Cleaned up {deleted_count} old backups")
        return deleted_count

    def get_backup_statistics(self) -> Dict[str, Any]:
        """Get backup statistics"""
        total_backups = len(self.backups)
        successful_backups = len([b for b in self.backups if b.status == "verified"])
        failed_backups = len([b for b in self.backups if b.status == "failed"])

        total_size = sum(b.size_bytes for b in self.backups)
        total_files = sum(b.file_count for b in self.backups)

        # Group by type
        type_counts = {}
        for backup in self.backups:
            backup_type = backup.backup_type
            type_counts[backup_type] = type_counts.get(backup_type, 0) + 1

        # Recent backups (last 7 days)
        recent_cutoff = time.time() - (7 * 24 * 3600)
        recent_backups = len([b for b in self.backups if b.created_at >= recent_cutoff])

        return {
            "total_backups": total_backups,
            "successful_backups": successful_backups,
            "failed_backups": failed_backups,
            "success_rate": successful_backups / total_backups if total_backups > 0 else 0,
            "total_size_bytes": total_size,
            "total_size_mb": total_size / (1024 * 1024),
            "total_files": total_files,
            "type_breakdown": type_counts,
            "recent_backups_7d": recent_backups,
            "oldest_backup": min(b.created_at for b in self.backups) if self.backups else None,
            "newest_backup": max(b.created_at for b in self.backups) if self.backups else None
        }

    def schedule_backup(self) -> Optional[BackupInfo]:
        """Schedule automatic backup based on configuration"""
        if not self.config["enabled"]:
            return None

        # Check if we need a full backup
        full_backup_days = self.config["schedule"]["full_backup_days"]
        last_full_backup = None

        for backup in reversed(self.backups):
            if backup.backup_type == "full" and backup.status == "verified":
                last_full_backup = backup
                break

        current_time = time.time()

        # Determine backup type
        if not last_full_backup or (current_time - last_full_backup.created_at) >= (full_backup_days * 24 * 3600):
            backup_type = "full"
            description = "Scheduled full backup"
        else:
            backup_type = "incremental"
            description = "Scheduled incremental backup"

        try:
            return self.create_backup(backup_type, description)
        except Exception as e:
            logger.error(f"Scheduled backup failed: {e}")
            return None

# Global backup manager instance
backup_manager = BackupManager()

def create_backup(backup_type: str = "full", description: str = "") -> BackupInfo:
    """Create a backup"""
    return backup_manager.create_backup(backup_type, description)

def restore_backup(backup_id: str, target_path: str = None, verify: bool = True) -> RestoreInfo:
    """Restore from backup"""
    return backup_manager.restore_backup(backup_id, target_path, verify)

def list_backups(backup_type: str = None) -> List[BackupInfo]:
    """List available backups"""
    return backup_manager.list_backups(backup_type)

def get_backup_statistics() -> Dict[str, Any]:
    """Get backup statistics"""
    return backup_manager.get_backup_statistics()

def cleanup_old_backups() -> int:
    """Clean up old backups"""
    return backup_manager.cleanup_old_backups()

def schedule_backup() -> Optional[BackupInfo]:
    """Schedule automatic backup"""
    return backup_manager.schedule_backup()
