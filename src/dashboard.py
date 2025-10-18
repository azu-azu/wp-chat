# src/dashboard.py - Dashboard and visualization functionality
import json
import os
import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import statistics

class DashboardData:
    """Dashboard data aggregation and visualization"""

    def __init__(self, logs_dir: str = "logs"):
        self.logs_dir = logs_dir
        self._ensure_logs_dir()

    def _ensure_logs_dir(self):
        """Ensure logs directory exists"""
        os.makedirs(self.logs_dir, exist_ok=True)

    def get_ab_metrics_summary(self, days: int = 7) -> Dict[str, Any]:
        """Get A/B testing metrics summary"""
        try:
            ab_file = os.path.join(self.logs_dir, "ab_metrics.jsonl")
            if not os.path.exists(ab_file):
                return {"message": "No A/B metrics available"}

            cutoff_time = time.time() - (days * 24 * 3600)

            # Parse A/B metrics
            rerank_on = []
            rerank_off = []

            with open(ab_file, 'r') as f:
                for line in f:
                    try:
                        data = json.loads(line.strip())
                        timestamp = data.get('timestamp', 0)
                        if isinstance(timestamp, str):
                            try:
                                timestamp = float(timestamp)
                            except ValueError:
                                # Try parsing ISO format
                                from datetime import datetime
                                try:
                                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                                    timestamp = dt.timestamp()
                                except ValueError:
                                    continue
                        if timestamp < cutoff_time:
                            continue

                        if data.get('rerank_enabled', False):
                            rerank_on.append(data)
                        else:
                            rerank_off.append(data)
                    except json.JSONDecodeError:
                        continue

            # Calculate metrics
            def calc_metrics(data_list):
                if not data_list:
                    return {
                        "total_requests": 0,
                        "avg_latency_ms": 0,
                        "p95_latency_ms": 0,
                        "success_rate": 0,
                        "avg_result_count": 0
                    }

                latencies = [d.get('latency_ms', 0) for d in data_list]
                success_count = sum(1 for d in data_list if d.get('status_code', 200) < 400)
                result_counts = [d.get('result_count', 0) for d in data_list]

                return {
                    "total_requests": len(data_list),
                    "avg_latency_ms": statistics.mean(latencies) if latencies else 0,
                    "p95_latency_ms": statistics.quantiles(latencies, n=20)[18] if len(latencies) > 1 else latencies[0] if latencies else 0,
                    "success_rate": success_count / len(data_list) if data_list else 0,
                    "avg_result_count": statistics.mean(result_counts) if result_counts else 0
                }

            rerank_on_metrics = calc_metrics(rerank_on)
            rerank_off_metrics = calc_metrics(rerank_off)

            # Calculate improvement
            improvement = {}
            if rerank_off_metrics["avg_latency_ms"] > 0:
                improvement["latency_change_pct"] = (
                    (rerank_on_metrics["avg_latency_ms"] - rerank_off_metrics["avg_latency_ms"])
                    / rerank_off_metrics["avg_latency_ms"] * 100
                )

            if rerank_off_metrics["success_rate"] > 0:
                improvement["success_rate_change_pct"] = (
                    (rerank_on_metrics["success_rate"] - rerank_off_metrics["success_rate"])
                    / rerank_off_metrics["success_rate"] * 100
                )

            return {
                "period_days": days,
                "rerank_on": rerank_on_metrics,
                "rerank_off": rerank_off_metrics,
                "improvement": improvement,
                "total_requests": len(rerank_on) + len(rerank_off)
            }

        except Exception as e:
            return {"error": str(e)}

    def get_cache_efficiency_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get cache efficiency metrics"""
        try:
            slo_file = os.path.join(self.logs_dir, "slo_metrics.jsonl")
            if not os.path.exists(slo_file):
                return {"message": "No cache metrics available"}

            cutoff_time = time.time() - (hours * 3600)

            cache_hits = 0
            cache_misses = 0
            total_requests = 0

            with open(slo_file, 'r') as f:
                for line in f:
                    try:
                        data = json.loads(line.strip())
                        if data.get('timestamp', 0) < cutoff_time:
                            continue

                        total_requests += 1
                        if data.get('cache_hit', False):
                            cache_hits += 1
                        else:
                            cache_misses += 1
                    except json.JSONDecodeError:
                        continue

            hit_rate = cache_hits / total_requests if total_requests > 0 else 0

            return {
                "period_hours": hours,
                "total_requests": total_requests,
                "cache_hits": cache_hits,
                "cache_misses": cache_misses,
                "hit_rate": hit_rate,
                "hit_rate_pct": hit_rate * 100
            }

        except Exception as e:
            return {"error": str(e)}

    def get_performance_trends(self, hours: int = 24) -> Dict[str, Any]:
        """Get performance trends over time"""
        try:
            slo_file = os.path.join(self.logs_dir, "slo_metrics.jsonl")
            if not os.path.exists(slo_file):
                return {"message": "No performance metrics available"}

            cutoff_time = time.time() - (hours * 3600)

            # Group by hour
            hourly_data = defaultdict(list)

            with open(slo_file, 'r') as f:
                for line in f:
                    try:
                        data = json.loads(line.strip())
                        if data.get('timestamp', 0) < cutoff_time:
                            continue

                        hour_key = int(data['timestamp'] // 3600) * 3600
                        hourly_data[hour_key].append(data)
                    except json.JSONDecodeError:
                        continue

            # Calculate hourly metrics
            trends = []
            for hour_timestamp in sorted(hourly_data.keys()):
                hour_data = hourly_data[hour_timestamp]
                latencies = [d.get('latency_ms', 0) for d in hour_data]
                success_count = sum(1 for d in hour_data if d.get('status_code', 200) < 400)
                cache_hits = sum(1 for d in hour_data if d.get('cache_hit', False))

                trends.append({
                    "timestamp": hour_timestamp,
                    "datetime": datetime.fromtimestamp(hour_timestamp).isoformat(),
                    "total_requests": len(hour_data),
                    "avg_latency_ms": statistics.mean(latencies) if latencies else 0,
                    "p95_latency_ms": statistics.quantiles(latencies, n=20)[18] if len(latencies) > 1 else latencies[0] if latencies else 0,
                    "success_rate": success_count / len(hour_data) if hour_data else 0,
                    "cache_hit_rate": cache_hits / len(hour_data) if hour_data else 0
                })

            return {
                "period_hours": hours,
                "trends": trends
            }

        except Exception as e:
            return {"error": str(e)}

    def get_system_health_summary(self) -> Dict[str, Any]:
        """Get overall system health summary"""
        try:
            # Get recent SLO status
            slo_file = os.path.join(self.logs_dir, "slo_alerts.jsonl")
            recent_alerts = []

            if os.path.exists(slo_file):
                cutoff_time = time.time() - (24 * 3600)  # Last 24 hours

                with open(slo_file, 'r') as f:
                    for line in f:
                        try:
                            data = json.loads(line.strip())
                            if data.get('timestamp', 0) >= cutoff_time:
                                recent_alerts.append(data)
                        except json.JSONDecodeError:
                            continue

            # Categorize alerts by severity
            critical_alerts = [a for a in recent_alerts if a.get('severity') == 'critical']
            warning_alerts = [a for a in recent_alerts if a.get('severity') == 'warning']

            # Determine overall health
            if critical_alerts:
                health_status = "critical"
            elif warning_alerts:
                health_status = "warning"
            else:
                health_status = "healthy"

            return {
                "status": health_status,
                "total_alerts_24h": len(recent_alerts),
                "critical_alerts": len(critical_alerts),
                "warning_alerts": len(warning_alerts),
                "recent_alerts": recent_alerts[-10:] if recent_alerts else []  # Last 10 alerts
            }

        except Exception as e:
            return {"error": str(e)}

    def get_dashboard_data(self, days: int = 7, hours: int = 24) -> Dict[str, Any]:
        """Get comprehensive dashboard data"""
        return {
            "timestamp": time.time(),
            "datetime": datetime.now().isoformat(),
            "ab_metrics": self.get_ab_metrics_summary(days),
            "cache_efficiency": self.get_cache_efficiency_summary(hours),
            "performance_trends": self.get_performance_trends(hours),
            "system_health": self.get_system_health_summary()
        }

# Global dashboard instance
dashboard = DashboardData()

def get_dashboard_data(days: int = 7, hours: int = 24) -> Dict[str, Any]:
    """Get dashboard data"""
    return dashboard.get_dashboard_data(days, hours)

def get_ab_summary(days: int = 7) -> Dict[str, Any]:
    """Get A/B testing summary"""
    return dashboard.get_ab_metrics_summary(days)

def get_cache_summary(hours: int = 24) -> Dict[str, Any]:
    """Get cache efficiency summary"""
    return dashboard.get_cache_efficiency_summary(hours)

def get_performance_summary(hours: int = 24) -> Dict[str, Any]:
    """Get performance trends summary"""
    return dashboard.get_performance_trends(hours)
