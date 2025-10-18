# src/model_manager.py - Model selection and device management
import torch
import logging
from typing import Optional, Dict, Any
from config import get_config_value

logger = logging.getLogger(__name__)

class ModelManager:
    def __init__(self):
        self.device_info = self._detect_device()
        self.model_config = self._load_model_config()

    def _detect_device(self) -> Dict[str, Any]:
        """Detect available compute devices"""
        device_info = {
            "cuda_available": torch.cuda.is_available(),
            "mps_available": hasattr(torch.backends, 'mps') and torch.backends.mps.is_available(),
            "cpu_available": True,
            "recommended_device": "cpu",
            "recommended_model": "cpu"
        }

        # Determine recommended device
        if device_info["cuda_available"]:
            device_info["recommended_device"] = "cuda"
            device_info["recommended_model"] = "gpu"
            logger.info(f"CUDA available: {torch.cuda.get_device_name(0)}")
        elif device_info["mps_available"]:
            device_info["recommended_device"] = "mps"
            device_info["recommended_model"] = "gpu"  # MPS can handle GPU models
            logger.info("MPS (Apple Silicon) available")
        else:
            logger.info("Using CPU for Cross-Encoder")

        return device_info

    def _load_model_config(self) -> Dict[str, Any]:
        """Load model configuration from config.yml"""
        return {
            "auto_detect": get_config_value("reranker.auto_detect", True),
            "fallback_to_cpu": get_config_value("reranker.fallback_to_cpu", True),
            "models": {
                "cpu": get_config_value("reranker.models.cpu", "cross-encoder/ms-marco-MiniLM-L-6-v2"),
                "gpu": get_config_value("reranker.models.gpu", "cross-encoder/ms-marco-MiniLM-L-12-v2"),
                "fallback": get_config_value("reranker.models.fallback", "cross-encoder/ms-marco-MiniLM-L-6-v2")
            },
            "batch_size": get_config_value("reranker.batch_size", 16),
            "timeout_sec": get_config_value("reranker.timeout_sec", 5.0),
            "device_override": get_config_value("reranker.device", None)
        }

    def get_model_config(self) -> Dict[str, Any]:
        """Get the optimal model configuration based on environment"""
        config = self.model_config.copy()

        # Apply device override if specified
        if config["device_override"]:
            config["device"] = config["device_override"]
            config["model_name"] = self._get_model_for_device(config["device_override"])
            logger.info(f"Using device override: {config['device']}")
        elif config["auto_detect"]:
            config["device"] = self.device_info["recommended_device"]
            config["model_name"] = self._get_model_for_device(config["device"])
            logger.info(f"Auto-detected device: {config['device']}")
        else:
            # Use CPU by default
            config["device"] = "cpu"
            config["model_name"] = config["models"]["cpu"]
            logger.info("Using default CPU configuration")

        return config

    def _get_model_for_device(self, device: str) -> str:
        """Get appropriate model name for device"""
        if device in ["cuda", "mps"]:
            return self.model_config["models"]["gpu"]
        else:
            return self.model_config["models"]["cpu"]

    def get_fallback_config(self) -> Dict[str, Any]:
        """Get fallback configuration for error cases"""
        return {
            "device": "cpu",
            "model_name": self.model_config["models"]["fallback"],
            "batch_size": self.model_config["batch_size"],
            "timeout_sec": self.model_config["timeout_sec"]
        }

    def get_device_info(self) -> Dict[str, Any]:
        """Get device information for debugging"""
        return {
            "device_info": self.device_info,
            "model_config": self.model_config,
            "current_config": self.get_model_config()
        }

# Global model manager instance
model_manager = ModelManager()

def get_optimal_model_config() -> Dict[str, Any]:
    """Get optimal model configuration for current environment"""
    return model_manager.get_model_config()

def get_device_status() -> Dict[str, Any]:
    """Get device status and configuration info"""
    return model_manager.get_device_info()
