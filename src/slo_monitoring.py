# src/slo_monitoring.py - SLO monitoring and alerting
import time
import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
import statistics

@dataclass
class SLOTarget:
    """SLO target definition"""
    name: str
    target_p95_ms: int  # Target p95 latency in milliseconds
    target_success_rate: float  # Target success rate (0.0-1.0)
    window_minutes: int  # Monitoring window in minutes
    alert_threshold: float  # Alert threshold (0.0-1.0)

@dataclass
class MetricPoint:
    """Single metric measurement"""
    timestamp: float
    endpoint: str
    latency_ms: int
    status_code: int
    rerank_enabled: bool
    cache_hit: bool
    fallback_used: bool
    error_message: Optional[str] = None

@dataclass
class SLOMetrics:
    """SLO metrics for a time window"""
    window_start: float
    window_end: float
    total_requests: int
    successful_requests: int
    failed_requests: int
    p95_latency_ms: float
    p99_latency_ms: float
    avg_latency_ms: float
    success_rate: float
    rerank_rate: float
    cache_hit_rate: float
    fallback_rate: float
    error_rate: float

class SLOMonitor:
    """SLO monitoring and alerting system"""

    def __init__(self, metrics_file: str = "logs/slo_metrics.jsonl",
                 alerts_file: str = "logs/slo_alerts.jsonl"):
        self.metrics_file = metrics_file
        self.alerts_file = alerts_file
        self.metrics_buffer: deque = deque(maxlen=10000)  # Keep last 10k metrics
        self._ensure_logs_dir()

        # Default SLO targets
        self.slo_targets = {
            "search": SLOTarget(
                name="search",
                target_p95_ms=800,
                target_success_rate=0.995,
                window_minutes=5,
                alert_threshold=0.9
            ),
            "ask": SLOTarget(
                name="ask",
                target_p95_ms=1000,
                target_success_rate=0.99,
                window_minutes=5,
                alert_threshold=0.9
            )
        }

    def _ensure_logs_dir(self):
        """Ensure logs directory exists"""
        os.makedirs(os.path.dirname(self.metrics_file), exist_ok=True)
        os.makedirs(os.path.dirname(self.alerts_file), exist_ok=True)

    def record_metric(self, endpoint: str, latency_ms: int, status_code: int,
                     rerank_enabled: bool = False, cache_hit: bool = False,
                     fallback_used: bool = False, error_message: Optional[str] = None):
        """Record a single metric point"""
        metric = MetricPoint(
            timestamp=time.time(),
            endpoint=endpoint,
            latency_ms=latency_ms,
            status_code=status_code,
            rerank_enabled=rerank_enabled,
            cache_hit=cache_hit,
            fallback_used=fallback_used,
            error_message=error_message
        )

        # Add to buffer
        self.metrics_buffer.append(metric)

        # Write to file
        try:
            with open(self.metrics_file, 'a') as f:
                f.write(json.dumps(asdict(metric)) + '\n')
        except Exception as e:
            print(f"Failed to write metric: {e}")

    def calculate_slo_metrics(self, endpoint: str, window_minutes: int = 5) -> Optional[SLOMetrics]:
        """Calculate SLO metrics for a time window"""
        current_time = time.time()
        window_start = current_time - (window_minutes * 60)

        # Filter metrics for endpoint and time window
        window_metrics = [
            m for m in self.metrics_buffer
            if m.endpoint == endpoint and m.timestamp >= window_start
        ]

        if not window_metrics:
            return None

        # Calculate basic metrics
        total_requests = len(window_metrics)
        successful_requests = sum(1 for m in window_metrics if 200 <= m.status_code < 300)
        failed_requests = total_requests - successful_requests

        # Calculate latencies
        latencies = [m.latency_ms for m in window_metrics]
        p95_latency_ms = statistics.quantiles(latencies, n=20)[18] if len(latencies) > 1 else latencies[0]
        p99_latency_ms = statistics.quantiles(latencies, n=100)[98] if len(latencies) > 1 else latencies[0]
        avg_latency_ms = statistics.mean(latencies)

        # Calculate rates
        success_rate = successful_requests / total_requests if total_requests > 0 else 0
        rerank_rate = sum(1 for m in window_metrics if m.rerank_enabled) / total_requests if total_requests > 0 else 0
        cache_hit_rate = sum(1 for m in window_metrics if m.cache_hit) / total_requests if total_requests > 0 else 0
        fallback_rate = sum(1 for m in window_metrics if m.fallback_used) / total_requests if total_requests > 0 else 0
        error_rate = failed_requests / total_requests if total_requests > 0 else 0

        return SLOMetrics(
            window_start=window_start,
            window_end=current_time,
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            p95_latency_ms=p95_latency_ms,
            p99_latency_ms=p99_latency_ms,
            avg_latency_ms=avg_latency_ms,
            success_rate=success_rate,
            rerank_rate=rerank_rate,
            cache_hit_rate=cache_hit_rate,
            fallback_rate=fallback_rate,
            error_rate=error_rate
        )

    def check_slo_violations(self, endpoint: str) -> List[Dict[str, Any]]:
        """Check for SLO violations and generate alerts"""
        if endpoint not in self.slo_targets:
            return []

        target = self.slo_targets[endpoint]
        metrics = self.calculate_slo_metrics(endpoint, target.window_minutes)

        if not metrics:
            return []

        violations = []

        # Check latency SLO
        if metrics.p95_latency_ms > target.target_p95_ms:
            violations.append({
                "type": "latency_slo_violation",
                "endpoint": endpoint,
                "metric": "p95_latency_ms",
                "actual": metrics.p95_latency_ms,
                "target": target.target_p95_ms,
                "severity": "warning",
                "message": f"p95 latency {metrics.p95_latency_ms:.1f}ms exceeds target {target.target_p95_ms}ms"
            })

        # Check success rate SLO
        if metrics.success_rate < target.target_success_rate:
            violations.append({
                "type": "success_rate_slo_violation",
                "endpoint": endpoint,
                "metric": "success_rate",
                "actual": metrics.success_rate,
                "target": target.target_success_rate,
                "severity": "critical",
                "message": f"Success rate {metrics.success_rate:.3f} below target {target.target_success_rate:.3f}"
            })

        # Check error rate threshold
        if metrics.error_rate > (1 - target.target_success_rate) * target.alert_threshold:
            violations.append({
                "type": "error_rate_threshold",
                "endpoint": endpoint,
                "metric": "error_rate",
                "actual": metrics.error_rate,
                "threshold": (1 - target.target_success_rate) * target.alert_threshold,
                "severity": "warning",
                "message": f"Error rate {metrics.error_rate:.3f} exceeds threshold"
            })

        # Check for high fallback rate
        if metrics.fallback_rate > 0.1:  # More than 10% fallback
            violations.append({
                "type": "high_fallback_rate",
                "endpoint": endpoint,
                "metric": "fallback_rate",
                "actual": metrics.fallback_rate,
                "threshold": 0.1,
                "severity": "warning",
                "message": f"High fallback rate {metrics.fallback_rate:.3f}"
            })

        return violations

    def generate_alert(self, violation: Dict[str, Any]):
        """Generate and log an alert"""
        alert = {
            "timestamp": time.time(),
            "datetime": datetime.now().isoformat(),
            "alert_id": f"{violation['type']}_{violation['endpoint']}_{int(time.time())}",
            **violation
        }

        try:
            with open(self.alerts_file, 'a') as f:
                f.write(json.dumps(alert) + '\n')
        except Exception as e:
            print(f"Failed to write alert: {e}")

        # Print alert to console
        print(f"🚨 ALERT [{violation['severity'].upper()}] {violation['message']}")

    def monitor_slos(self):
        """Monitor all SLOs and generate alerts"""
        for endpoint in self.slo_targets.keys():
            violations = self.check_slo_violations(endpoint)
            for violation in violations:
                self.generate_alert(violation)

    def get_slo_status(self) -> Dict[str, Any]:
        """Get current SLO status for all endpoints"""
        status = {}

        for endpoint, target in self.slo_targets.items():
            metrics = self.calculate_slo_metrics(endpoint, target.window_minutes)
            violations = self.check_slo_violations(endpoint)

            status[endpoint] = {
                "target": asdict(target),
                "metrics": asdict(metrics) if metrics else None,
                "violations": violations,
                "status": "healthy" if not violations else "degraded"
            }

        return status

    def get_metrics_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get metrics summary for the last N hours"""
        current_time = time.time()
        window_start = current_time - (hours * 3600)

        # Filter metrics for time window
        window_metrics = [
            m for m in self.metrics_buffer
            if m.timestamp >= window_start
        ]

        if not window_metrics:
            return {"message": "No metrics available"}

        # Group by endpoint
        by_endpoint = defaultdict(list)
        for metric in window_metrics:
            by_endpoint[metric.endpoint].append(metric)

        summary = {}
        for endpoint, metrics in by_endpoint.items():
            latencies = [m.latency_ms for m in metrics]
            success_count = sum(1 for m in metrics if 200 <= m.status_code < 300)

            summary[endpoint] = {
                "total_requests": len(metrics),
                "success_rate": success_count / len(metrics),
                "avg_latency_ms": statistics.mean(latencies),
                "p95_latency_ms": statistics.quantiles(latencies, n=20)[18] if len(latencies) > 1 else latencies[0],
                "p99_latency_ms": statistics.quantiles(latencies, n=100)[98] if len(latencies) > 1 else latencies[0],
                "rerank_rate": sum(1 for m in metrics if m.rerank_enabled) / len(metrics),
                "cache_hit_rate": sum(1 for m in metrics if m.cache_hit) / len(metrics),
                "fallback_rate": sum(1 for m in metrics if m.fallback_used) / len(metrics)
            }

        return summary

# Global SLO monitor instance
slo_monitor = SLOMonitor()

def record_api_metric(endpoint: str, latency_ms: int, status_code: int,
                     rerank_enabled: bool = False, cache_hit: bool = False,
                     fallback_used: bool = False, error_message: Optional[str] = None):
    """Convenience function to record API metrics"""
    slo_monitor.record_metric(endpoint, latency_ms, status_code,
                             rerank_enabled, cache_hit, fallback_used, error_message)

def get_slo_status() -> Dict[str, Any]:
    """Get current SLO status"""
    return slo_monitor.get_slo_status()

def get_metrics_summary(hours: int = 24) -> Dict[str, Any]:
    """Get metrics summary"""
    return slo_monitor.get_metrics_summary(hours)
