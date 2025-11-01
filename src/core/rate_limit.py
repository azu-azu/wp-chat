# src/rate_limit.py - Rate limiting functionality
import json
import os
import time


class RateLimiter:
    """Rate limiter with sliding window and IP-based tracking"""

    def __init__(self, cache_dir: str = "cache"):
        self.cache_dir = cache_dir
        self.rate_limit_file = os.path.join(cache_dir, "rate_limits.json")
        self._ensure_cache_dir()
        self._load_rate_limits()

    def _ensure_cache_dir(self):
        """Ensure cache directory exists"""
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir, exist_ok=True)

    def _load_rate_limits(self):
        """Load rate limit data from file"""
        try:
            if os.path.exists(self.rate_limit_file):
                with open(self.rate_limit_file) as f:
                    self.rate_limits = json.load(f)
            else:
                self.rate_limits = {}
        except (json.JSONDecodeError, FileNotFoundError):
            self.rate_limits = {}

    def _save_rate_limits(self):
        """Save rate limit data to file"""
        try:
            with open(self.rate_limit_file, "w") as f:
                json.dump(self.rate_limits, f)
        except Exception as e:
            print(f"Failed to save rate limits: {e}")

    def _cleanup_old_entries(self, client_id: str, window_seconds: int):
        """Remove old entries outside the time window"""
        current_time = time.time()
        cutoff_time = current_time - window_seconds

        if client_id in self.rate_limits:
            # Keep only recent entries
            self.rate_limits[client_id] = [
                entry for entry in self.rate_limits[client_id] if entry > cutoff_time
            ]

    def is_allowed(
        self, client_id: str, max_requests: int = 100, window_seconds: int = 3600
    ) -> tuple[bool, dict[str, int]]:
        """
        Check if request is allowed based on rate limit

        Args:
            client_id: Unique identifier (IP address, user ID, etc.)
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds

        Returns:
            (is_allowed, rate_info)
        """
        current_time = time.time()

        # Initialize client if not exists
        if client_id not in self.rate_limits:
            self.rate_limits[client_id] = []

        # Cleanup old entries
        self._cleanup_old_entries(client_id, window_seconds)

        # Check current request count
        current_requests = len(self.rate_limits[client_id])

        # Rate limit info
        rate_info = {
            "requests": current_requests,
            "limit": max_requests,
            "window_seconds": window_seconds,
            "reset_time": current_time + window_seconds,
            "remaining": max(0, max_requests - current_requests),
        }

        # Check if under limit
        if current_requests < max_requests:
            # Add current request
            self.rate_limits[client_id].append(current_time)
            self._save_rate_limits()
            return True, rate_info
        else:
            return False, rate_info

    def get_client_stats(self, client_id: str) -> dict[str, int]:
        """Get rate limit statistics for a client"""
        if client_id not in self.rate_limits:
            return {"requests": 0, "limit": 100, "window_seconds": 3600, "remaining": 100}

        current_time = time.time()
        window_seconds = 3600  # Default window
        cutoff_time = current_time - window_seconds

        # Count recent requests
        recent_requests = [entry for entry in self.rate_limits[client_id] if entry > cutoff_time]

        return {
            "requests": len(recent_requests),
            "limit": 100,
            "window_seconds": window_seconds,
            "remaining": max(0, 100 - len(recent_requests)),
        }

    def reset_client(self, client_id: str) -> bool:
        """Reset rate limit for a specific client"""
        try:
            if client_id in self.rate_limits:
                del self.rate_limits[client_id]
                self._save_rate_limits()
            return True
        except Exception:
            return False

    def get_global_stats(self) -> dict[str, any]:
        """Get global rate limiting statistics"""
        current_time = time.time()
        window_seconds = 3600
        cutoff_time = current_time - window_seconds

        total_clients = len(self.rate_limits)
        active_clients = 0
        total_requests = 0

        for client_id, requests in self.rate_limits.items():
            recent_requests = [r for r in requests if r > cutoff_time]
            if recent_requests:
                active_clients += 1
                total_requests += len(recent_requests)

        return {
            "total_clients": total_clients,
            "active_clients": active_clients,
            "total_requests_last_hour": total_requests,
            "average_requests_per_client": round(total_requests / max(active_clients, 1), 2),
        }


# Global rate limiter instance
rate_limiter = RateLimiter()


def get_client_id(request) -> str:
    """Extract client ID from request (IP address)"""
    # Try to get real IP from headers (for reverse proxy scenarios)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    # Fallback to direct client IP
    return request.client.host


def check_rate_limit(
    request, max_requests: int = 100, window_seconds: int = 3600
) -> tuple[bool, dict[str, int]]:
    """Check rate limit for a request"""
    client_id = get_client_id(request)
    return rate_limiter.is_allowed(client_id, max_requests, window_seconds)


def get_rate_limit_headers(rate_info: dict[str, int]) -> dict[str, str]:
    """Generate rate limit headers for HTTP response"""
    return {
        "X-RateLimit-Limit": str(rate_info["limit"]),
        "X-RateLimit-Remaining": str(rate_info["remaining"]),
        "X-RateLimit-Reset": str(int(rate_info["reset_time"])),
        "X-RateLimit-Window": str(rate_info["window_seconds"]),
    }
