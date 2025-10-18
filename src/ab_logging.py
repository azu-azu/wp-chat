# src/logging.py - A/B logging and metrics collection
import json
import time
import os
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import Request, Response
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ABLogger:
    def __init__(self, log_file: str = "logs/ab_metrics.jsonl"):
        self.log_file = log_file
        self.ensure_log_directory()

    def ensure_log_directory(self):
        """Ensure log directory exists"""
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)

    def log_search_metrics(self,
                        query: str,
                        rerank_enabled: bool,
                        latency_ms: float,
                        result_count: int,
                        mode: str = "hybrid",
                        topk: int = 5,
                        user_agent: Optional[str] = None,
                        ip_address: Optional[str] = None):
        """Log A/B search metrics"""

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": "search",
            "query": query,
            "rerank_enabled": rerank_enabled,
            "mode": mode,
            "topk": topk,
            "latency_ms": round(latency_ms, 2),
            "result_count": result_count,
            "user_agent": user_agent,
            "ip_address": ip_address
        }

        self._write_log(log_entry)

    def log_ask_metrics(self,
                    question: str,
                    rerank_enabled: bool,
                    highlight_enabled: bool,
                    latency_ms: float,
                    result_count: int,
                    mode: str = "hybrid",
                    topk: int = 5,
                    user_agent: Optional[str] = None,
                    ip_address: Optional[str] = None):
        """Log A/B ask metrics"""

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": "ask",
            "question": question,
            "rerank_enabled": rerank_enabled,
            "highlight_enabled": highlight_enabled,
            "mode": mode,
            "topk": topk,
            "latency_ms": round(latency_ms, 2),
            "result_count": result_count,
            "user_agent": user_agent,
            "ip_address": ip_address
        }

        self._write_log(log_entry)

    def _write_log(self, log_entry: Dict[str, Any]):
        """Write log entry to file"""
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"Failed to write log entry: {e}")

# Global logger instance
ab_logger = ABLogger()

async def ab_logging_middleware(request: Request, call_next):
    """FastAPI middleware for A/B logging"""
    start_time = time.time()

    # Process request
    response = await call_next(request)

    # Calculate latency
    latency_ms = (time.time() - start_time) * 1000

    # Extract request info
    path = str(request.url.path)
    query_params = dict(request.query_params)
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    # Log based on endpoint
    try:
        if path == "/search":
            ab_logger.log_search_metrics(
                query=query_params.get("q", ""),
                rerank_enabled=query_params.get("rerank", "false").lower() == "true",
                latency_ms=latency_ms,
                result_count=0,  # Will be updated after response processing
                mode=query_params.get("mode", "hybrid"),
                topk=int(query_params.get("topk", 5)),
                user_agent=user_agent,
                ip_address=client_ip
            )
        elif path == "/ask":
            # For POST requests, we'll need to extract from request body
            # This will be handled in the endpoint itself
            pass

    except Exception as e:
        logger.error(f"A/B logging error: {e}")

    return response

def get_ab_stats(days: int = 7) -> Dict[str, Any]:
    """Get A/B statistics from logs"""
    try:
        stats = {
            "total_searches": 0,
            "rerank_enabled": 0,
            "rerank_disabled": 0,
            "avg_latency_rerank": 0,
            "avg_latency_no_rerank": 0,
            "avg_result_count": 0,
            "queries": {}
        }

        if not os.path.exists(ab_logger.log_file):
            return stats

        rerank_latencies = []
        no_rerank_latencies = []
        result_counts = []

        with open(ab_logger.log_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    if entry.get("event_type") == "search":
                        stats["total_searches"] += 1

                        if entry.get("rerank_enabled"):
                            stats["rerank_enabled"] += 1
                            rerank_latencies.append(entry.get("latency_ms", 0))
                        else:
                            stats["rerank_disabled"] += 1
                            no_rerank_latencies.append(entry.get("latency_ms", 0))

                        result_counts.append(entry.get("result_count", 0))

                        # Track unique queries
                        query = entry.get("query", "")
                        if query:
                            stats["queries"][query] = stats["queries"].get(query, 0) + 1

                except json.JSONDecodeError:
                    continue

        # Calculate averages
        if rerank_latencies:
            stats["avg_latency_rerank"] = round(sum(rerank_latencies) / len(rerank_latencies), 2)
        if no_rerank_latencies:
            stats["avg_latency_no_rerank"] = round(sum(no_rerank_latencies) / len(no_rerank_latencies), 2)
        if result_counts:
            stats["avg_result_count"] = round(sum(result_counts) / len(result_counts), 2)

        return stats

    except Exception as e:
        logger.error(f"Error getting A/B stats: {e}")
        return {"error": str(e)}
