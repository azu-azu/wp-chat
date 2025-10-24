# src/config.py - Configuration management
import yaml
import os
from typing import Dict, Any, Optional

CONFIG_FILE = "config.yml"

def load_config() -> Dict[str, Any]:
    """Load configuration from config.yml"""
    if not os.path.exists(CONFIG_FILE):
        # Return default config if file doesn't exist
        return get_default_config()

    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def get_default_config() -> Dict[str, Any]:
    """Return default configuration"""
    return {
        "hybrid": {
            "alpha": 0.6,
            "k_bm25": 100,
            "k_dense": 100
        },
        "mmr": {
            "lambda": 0.7,
            "topn": 30
        },
        "reranker": {
            "model_name": "cross-encoder/ms-marco-MiniLM-L-6-v2",
            "batch_size": 16,
            "timeout_sec": 5.0,
            "device": None
        },
        "api": {
            "topk_default": 5,
            "topk_max": 10,
            "snippet_length": 400
        },
        "eval": {
            "default_k": 5,
            "queries_file": "eval/queries.jsonl"
        }
    }

def get_config_value(path: str, default: Any = None) -> Any:
    """Get configuration value by dot-separated path (e.g., 'hybrid.alpha')"""
    config = load_config()
    keys = path.split('.')
    value = config

    try:
        for key in keys:
            value = value[key]
        return value
    except (KeyError, TypeError):
        return default

# Global config instance
_config = None

def get_config() -> Dict[str, Any]:
    """Get global config instance (cached)"""
    global _config
    if _config is None:
        _config = load_config()
    return _config
