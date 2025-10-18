# src/canary_manager.py - Canary deployment and feature toggle management
import json
import os
import time
import hashlib
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime
import threading
import logging

logger = logging.getLogger(__name__)

@dataclass
class CanaryConfig:
    """Canary deployment configuration"""
    enabled: bool = False
    rollout_percentage: float = 0.0  # 0.0 to 1.0
    user_seed: str = "default_seed"
    emergency_stop: bool = False
    auto_rollback_threshold: float = 0.05  # 5% error rate threshold
    latency_threshold_ms: int = 2000  # 2 second latency threshold
    min_requests_for_rollback: int = 100  # Minimum requests before considering rollback
    last_updated: float = 0.0
    updated_by: str = "system"

@dataclass
class CanaryMetrics:
    """Canary deployment metrics"""
    timestamp: float
    total_requests: int
    rerank_enabled_requests: int
    rerank_disabled_requests: int
    error_rate_enabled: float
    error_rate_disabled: float
    avg_latency_enabled: float
    avg_latency_disabled: float
    p95_latency_enabled: float
    p95_latency_disabled: float

class CanaryManager:
    """Manages canary deployment and feature toggles"""

    def __init__(self, config_file: str = "logs/canary_config.json",
                 metrics_file: str = "logs/canary_metrics.jsonl"):
        self.config_file = config_file
        self.metrics_file = metrics_file
        self.config = CanaryConfig()
        self.metrics_buffer: List[CanaryMetrics] = []
        self.lock = threading.Lock()
        self._ensure_logs_dir()
        self._load_config()

        # Start background monitoring
        self.monitoring_thread = threading.Thread(target=self._monitor_canary, daemon=True)
        self.monitoring_thread.start()

    def _ensure_logs_dir(self):
        """Ensure logs directory exists"""
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        os.makedirs(os.path.dirname(self.metrics_file), exist_ok=True)

    def _load_config(self):
        """Load canary configuration from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    self.config = CanaryConfig(**data)
                logger.info(f"Loaded canary config: {self.config.rollout_percentage:.1%} rollout")
            else:
                self._save_config()
        except Exception as e:
            logger.error(f"Failed to load canary config: {e}")
            self.config = CanaryConfig()

    def _save_config(self):
        """Save canary configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(asdict(self.config), f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save canary config: {e}")

    def is_rerank_enabled_for_user(self, user_id: str) -> bool:
        """Determine if rerank should be enabled for a specific user"""
        with self.lock:
            # Emergency stop overrides everything
            if self.config.emergency_stop:
                return False

            # If canary is disabled, return False
            if not self.config.enabled:
                return False

            # If rollout is 0%, no one gets rerank
            if self.config.rollout_percentage <= 0.0:
                return False

            # If rollout is 100%, everyone gets rerank
            if self.config.rollout_percentage >= 1.0:
                return True

            # Use consistent hashing to determine if user should get rerank
            user_hash = self._hash_user_id(user_id)
            return user_hash < self.config.rollout_percentage

    def _hash_user_id(self, user_id: str) -> float:
        """Generate consistent hash for user ID"""
        # Combine user ID with seed for consistent but configurable distribution
        combined = f"{user_id}:{self.config.user_seed}"
        hash_obj = hashlib.md5(combined.encode())
        # Convert to float between 0 and 1
        return int(hash_obj.hexdigest()[:8], 16) / 0xffffffff

    def update_rollout_percentage(self, percentage: float, updated_by: str = "admin"):
        """Update rollout percentage (0.0 to 1.0)"""
        with self.lock:
            percentage = max(0.0, min(1.0, percentage))  # Clamp to [0, 1]
            self.config.rollout_percentage = percentage
            self.config.enabled = percentage > 0.0
            self.config.last_updated = time.time()
            self.config.updated_by = updated_by
            self._save_config()

            logger.info(f"Updated rollout percentage to {percentage:.1%} by {updated_by}")

    def enable_canary(self, percentage: float = 0.1, updated_by: str = "admin"):
        """Enable canary deployment with specified percentage"""
        self.update_rollout_percentage(percentage, updated_by)

    def disable_canary(self, updated_by: str = "admin"):
        """Disable canary deployment (set to 0%)"""
        self.update_rollout_percentage(0.0, updated_by)

    def emergency_stop(self, updated_by: str = "admin"):
        """Emergency stop - immediately disable rerank for all users"""
        with self.lock:
            self.config.emergency_stop = True
            self.config.last_updated = time.time()
            self.config.updated_by = updated_by
            self._save_config()

            logger.warning(f"EMERGENCY STOP activated by {updated_by}")

    def clear_emergency_stop(self, updated_by: str = "admin"):
        """Clear emergency stop and restore previous rollout percentage"""
        with self.lock:
            self.config.emergency_stop = False
            self.config.last_updated = time.time()
            self.config.updated_by = updated_by
            self._save_config()

            logger.info(f"Emergency stop cleared by {updated_by}")

    def get_config(self) -> Dict[str, Any]:
        """Get current canary configuration"""
        with self.lock:
            return asdict(self.config)

    def record_canary_metric(self, user_id: str, rerank_enabled: bool,
                           latency_ms: int, status_code: int, error_message: Optional[str] = None):
        """Record a canary deployment metric"""
        # This will be called by the API to track canary performance
        pass  # Implementation will be added when integrating with API

    def _monitor_canary(self):
        """Background monitoring for automatic rollback"""
        while True:
            try:
                time.sleep(60)  # Check every minute

                if not self.config.enabled or self.config.emergency_stop:
                    continue

                # Check if we should auto-rollback
                if self._should_auto_rollback():
                    logger.warning("Auto-rollback triggered due to poor performance")
                    self.disable_canary("auto_rollback")

            except Exception as e:
                logger.error(f"Error in canary monitoring: {e}")

    def _should_auto_rollback(self) -> bool:
        """Determine if automatic rollback should be triggered"""
        # This is a simplified version - in production, you'd want more sophisticated logic
        # For now, we'll rely on the SLO monitoring system

        # Check recent metrics
        recent_metrics = self._get_recent_metrics(minutes=5)
        if not recent_metrics:
            return False

        # Simple rollback logic: if error rate is too high
        total_requests = sum(m.total_requests for m in recent_metrics)
        if total_requests < self.config.min_requests_for_rollback:
            return False

        # Calculate weighted error rate
        total_errors = 0
        for metrics in recent_metrics:
            total_errors += metrics.error_rate_enabled * metrics.rerank_enabled_requests

        error_rate = total_errors / total_requests if total_requests > 0 else 0

        return error_rate > self.config.auto_rollback_threshold

    def _get_recent_metrics(self, minutes: int = 5) -> List[CanaryMetrics]:
        """Get recent canary metrics"""
        cutoff_time = time.time() - (minutes * 60)
        return [m for m in self.metrics_buffer if m.timestamp >= cutoff_time]

    def get_canary_status(self) -> Dict[str, Any]:
        """Get comprehensive canary deployment status"""
        with self.lock:
            recent_metrics = self._get_recent_metrics(minutes=10)

            status = {
                "config": asdict(self.config),
                "status": "emergency_stop" if self.config.emergency_stop else
                         "disabled" if not self.config.enabled else
                         "active",
                "recent_metrics": [asdict(m) for m in recent_metrics[-5:]],  # Last 5 data points
                "summary": self._calculate_summary(recent_metrics)
            }

            return status

    def _calculate_summary(self, metrics: List[CanaryMetrics]) -> Dict[str, Any]:
        """Calculate summary statistics from metrics"""
        if not metrics:
            return {"message": "No recent metrics available"}

        total_requests = sum(m.total_requests for m in metrics)
        total_enabled = sum(m.rerank_enabled_requests for m in metrics)
        total_disabled = sum(m.rerank_disabled_requests for m in metrics)

        if total_enabled == 0:
            return {"message": "No rerank-enabled requests in recent period"}

        # Calculate weighted averages
        weighted_error_enabled = sum(m.error_rate_enabled * m.rerank_enabled_requests for m in metrics)
        weighted_error_disabled = sum(m.error_rate_disabled * m.rerank_disabled_requests for m in metrics)
        weighted_latency_enabled = sum(m.avg_latency_enabled * m.rerank_enabled_requests for m in metrics)
        weighted_latency_disabled = sum(m.avg_latency_disabled * m.rerank_disabled_requests for m in metrics)

        return {
            "total_requests": total_requests,
            "rerank_enabled_requests": total_enabled,
            "rerank_disabled_requests": total_disabled,
            "rollout_percentage": total_enabled / total_requests if total_requests > 0 else 0,
            "avg_error_rate_enabled": weighted_error_enabled / total_enabled if total_enabled > 0 else 0,
            "avg_error_rate_disabled": weighted_error_disabled / total_disabled if total_disabled > 0 else 0,
            "avg_latency_enabled": weighted_latency_enabled / total_enabled if total_enabled > 0 else 0,
            "avg_latency_disabled": weighted_latency_disabled / total_disabled if total_disabled > 0 else 0,
            "performance_impact": {
                "latency_change_pct": ((weighted_latency_enabled / total_enabled) -
                                      (weighted_latency_disabled / total_disabled)) /
                                     (weighted_latency_disabled / total_disabled) * 100
                                     if total_disabled > 0 and weighted_latency_disabled > 0 else 0,
                "error_rate_change_pct": ((weighted_error_enabled / total_enabled) -
                                        (weighted_error_disabled / total_disabled)) /
                                       (weighted_error_disabled / total_disabled) * 100
                                       if total_disabled > 0 and weighted_error_disabled > 0 else 0
            }
        }

# Global canary manager instance
canary_manager = CanaryManager()

def is_rerank_enabled_for_user(user_id: str) -> bool:
    """Check if rerank should be enabled for a user"""
    return canary_manager.is_rerank_enabled_for_user(user_id)

def update_canary_rollout(percentage: float, updated_by: str = "admin"):
    """Update canary rollout percentage"""
    canary_manager.update_rollout_percentage(percentage, updated_by)

def enable_canary(percentage: float = 0.1, updated_by: str = "admin"):
    """Enable canary deployment"""
    canary_manager.enable_canary(percentage, updated_by)

def disable_canary(updated_by: str = "admin"):
    """Disable canary deployment"""
    canary_manager.disable_canary(updated_by)

def emergency_stop_canary(updated_by: str = "admin"):
    """Emergency stop canary deployment"""
    canary_manager.emergency_stop(updated_by)

def clear_emergency_stop(updated_by: str = "admin"):
    """Clear emergency stop"""
    canary_manager.clear_emergency_stop(updated_by)

def get_canary_status() -> Dict[str, Any]:
    """Get canary deployment status"""
    return canary_manager.get_canary_status()
