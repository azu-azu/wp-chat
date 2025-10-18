# src/cache.py - Advanced caching functionality
import time
import hashlib
import json
import os
from typing import Any, Optional, Dict, List
from functools import wraps
import pickle

class CacheManager:
    """Advanced cache manager with TTL and size limits"""

    def __init__(self, cache_dir: str = "cache", max_size_mb: int = 100):
        self.cache_dir = cache_dir
        self.max_size_mb = max_size_mb
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self._ensure_cache_dir()

    def _ensure_cache_dir(self):
        """Ensure cache directory exists"""
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir, exist_ok=True)

    def _get_cache_path(self, key: str) -> str:
        """Get cache file path for key"""
        # Use hash to avoid filesystem issues with special characters
        hash_key = hashlib.md5(key.encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{hash_key}.cache")

    def _get_metadata_path(self, key: str) -> str:
        """Get metadata file path for key"""
        hash_key = hashlib.md5(key.encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{hash_key}.meta")

    def _is_expired(self, metadata: Dict) -> bool:
        """Check if cache entry is expired"""
        if "expires_at" not in metadata:
            return True
        return time.time() > metadata["expires_at"]

    def _cleanup_expired(self):
        """Remove expired cache entries"""
        if not os.path.exists(self.cache_dir):
            return

        for filename in os.listdir(self.cache_dir):
            if filename.endswith(".meta"):
                meta_path = os.path.join(self.cache_dir, filename)
                try:
                    with open(meta_path, 'r') as f:
                        metadata = json.load(f)
                    if self._is_expired(metadata):
                        cache_path = meta_path.replace(".meta", ".cache")
                        os.remove(meta_path)
                        if os.path.exists(cache_path):
                            os.remove(cache_path)
                except (json.JSONDecodeError, FileNotFoundError):
                    # Remove corrupted metadata files
                    os.remove(meta_path)

    def _get_cache_size(self) -> int:
        """Get total cache size in bytes"""
        total_size = 0
        if not os.path.exists(self.cache_dir):
            return 0

        for filename in os.listdir(self.cache_dir):
            if filename.endswith(".cache"):
                file_path = os.path.join(self.cache_dir, filename)
                total_size += os.path.getsize(file_path)
        return total_size

    def _evict_oldest(self):
        """Evict oldest cache entries when size limit exceeded"""
        if not os.path.exists(self.cache_dir):
            return

        # Get all cache files with their modification times
        cache_files = []
        for filename in os.listdir(self.cache_dir):
            if filename.endswith(".cache"):
                file_path = os.path.join(self.cache_dir, filename)
                meta_path = file_path.replace(".cache", ".meta")
                if os.path.exists(meta_path):
                    try:
                        with open(meta_path, 'r') as f:
                            metadata = json.load(f)
                        cache_files.append((file_path, meta_path, metadata.get("created_at", 0)))
                    except (json.JSONDecodeError, KeyError):
                        continue

        # Sort by creation time (oldest first)
        cache_files.sort(key=lambda x: x[2])

        # Remove oldest files until under size limit
        current_size = self._get_cache_size()
        for cache_path, meta_path, _ in cache_files:
            if current_size <= self.max_size_bytes:
                break
            try:
                file_size = os.path.getsize(cache_path)
                os.remove(cache_path)
                os.remove(meta_path)
                current_size -= file_size
            except FileNotFoundError:
                continue

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        cache_path = self._get_cache_path(key)
        meta_path = self._get_metadata_path(key)

        if not os.path.exists(cache_path) or not os.path.exists(meta_path):
            return None

        try:
            # Check metadata
            with open(meta_path, 'r') as f:
                metadata = json.load(f)

            if self._is_expired(metadata):
                # Remove expired entry
                os.remove(cache_path)
                os.remove(meta_path)
                return None

            # Load cached data
            with open(cache_path, 'rb') as f:
                return pickle.load(f)

        except (pickle.PickleError, json.JSONDecodeError, FileNotFoundError):
            # Remove corrupted cache files
            for path in [cache_path, meta_path]:
                if os.path.exists(path):
                    os.remove(path)
            return None

    def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> bool:
        """Set value in cache with TTL"""
        try:
            # Cleanup expired entries first
            self._cleanup_expired()

            # Check size limit and evict if necessary
            if self._get_cache_size() > self.max_size_bytes:
                self._evict_oldest()

            cache_path = self._get_cache_path(key)
            meta_path = self._get_metadata_path(key)

            # Save data
            with open(cache_path, 'wb') as f:
                pickle.dump(value, f)

            # Save metadata
            metadata = {
                "created_at": time.time(),
                "expires_at": time.time() + ttl_seconds,
                "key": key,
                "size": os.path.getsize(cache_path)
            }

            with open(meta_path, 'w') as f:
                json.dump(metadata, f)

            return True

        except Exception as e:
            print(f"Cache set error: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete cache entry"""
        cache_path = self._get_cache_path(key)
        meta_path = self._get_metadata_path(key)

        try:
            for path in [cache_path, meta_path]:
                if os.path.exists(path):
                    os.remove(path)
            return True
        except Exception:
            return False

    def clear(self) -> bool:
        """Clear all cache entries"""
        try:
            if os.path.exists(self.cache_dir):
                for filename in os.listdir(self.cache_dir):
                    file_path = os.path.join(self.cache_dir, filename)
                    os.remove(file_path)
            return True
        except Exception:
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        if not os.path.exists(self.cache_dir):
            return {
                "total_entries": 0,
                "total_size_mb": 0,
                "max_size_mb": self.max_size_mb,
                "hit_rate": 0
            }

        total_entries = 0
        total_size = 0
        expired_entries = 0

        for filename in os.listdir(self.cache_dir):
            if filename.endswith(".meta"):
                meta_path = os.path.join(self.cache_dir, filename)
                try:
                    with open(meta_path, 'r') as f:
                        metadata = json.load(f)
                    total_entries += 1
                    if not self._is_expired(metadata):
                        cache_path = meta_path.replace(".meta", ".cache")
                        if os.path.exists(cache_path):
                            total_size += os.path.getsize(cache_path)
                    else:
                        expired_entries += 1
                except (json.JSONDecodeError, FileNotFoundError):
                    continue

        return {
            "total_entries": total_entries,
            "active_entries": total_entries - expired_entries,
            "expired_entries": expired_entries,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "max_size_mb": self.max_size_mb,
            "utilization_percent": round((total_size / self.max_size_bytes) * 100, 1)
        }

# Global cache instance
cache_manager = CacheManager()

def cached(ttl_seconds: int = 3600, key_prefix: str = ""):
    """Decorator for caching function results"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            key_parts = [key_prefix, func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = "|".join(key_parts)

            # Try to get from cache
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result

            # Execute function and cache result
            result = func(*args, **kwargs)
            cache_manager.set(cache_key, result, ttl_seconds)
            return result

        return wrapper
    return decorator

def cache_search_results(query: str, results: List[Dict], ttl_seconds: int = 1800) -> bool:
    """Cache search results with query-specific TTL"""
    cache_key = f"search:{hashlib.md5(query.encode()).hexdigest()}"
    return cache_manager.set(cache_key, results, ttl_seconds)

def get_cached_search_results(query: str) -> Optional[List[Dict]]:
    """Get cached search results for query"""
    cache_key = f"search:{hashlib.md5(query.encode()).hexdigest()}"
    return cache_manager.get(cache_key)

def cache_embeddings(text: str, embeddings: Any, ttl_seconds: int = 7200) -> bool:
    """Cache embeddings with longer TTL"""
    cache_key = f"embeddings:{hashlib.md5(text.encode()).hexdigest()}"
    return cache_manager.set(cache_key, embeddings, ttl_seconds)

def get_cached_embeddings(text: str) -> Optional[Any]:
    """Get cached embeddings for text"""
    cache_key = f"embeddings:{hashlib.md5(text.encode()).hexdigest()}"
    return cache_manager.get(cache_key)
