"""Platform and GPU detection for conditional imports."""

from __future__ import annotations

import logging
import platform
import sys
from typing import Literal

logger = logging.getLogger(__name__)

# Platform detection
SYSTEM = platform.system()  # "Darwin" (macOS), "Linux", "Windows"
IS_MACOS = SYSTEM == "Darwin"
IS_LINUX = SYSTEM == "Linux"
IS_WINDOWS = SYSTEM == "Windows"
MACHINE = platform.machine()  # "arm64", "x86_64", "aarch64"

# GPU detection
CUDA_AVAILABLE = False
TORCH_AVAILABLE = False
VLLM_AVAILABLE = False

try:
    import torch

    TORCH_AVAILABLE = torch.cuda.is_available()
    CUDA_AVAILABLE = TORCH_AVAILABLE
    logger.info(f"PyTorch detected. CUDA available: {CUDA_AVAILABLE}")
except ImportError:
    logger.debug("PyTorch not found - CUDA detection skipped")

try:
    import vllm  # noqa: F401

    VLLM_AVAILABLE = True
    logger.info("vLLM detected - using real implementation")
except ImportError:
    logger.debug("vLLM not found - will use mock implementation for testing")


def get_mode() -> Literal["production", "development"]:
    """Determine execution mode based on platform and GPU availability.

    Returns:
        "production" — Linux with CUDA/GPU available (use real vLLM)
        "development" — macOS or no GPU (use mock vLLM for testing)
    """
    if VLLM_AVAILABLE and CUDA_AVAILABLE and IS_LINUX:
        return "production"
    return "development"


def should_use_mock_vllm() -> bool:
    """Check if mock vLLM should be used instead of real vLLM.

    Returns True if:
    - Running on macOS (no CUDA support)
    - CUDA not available
    - vLLM not installed
    """
    if IS_MACOS:
        logger.debug("macOS detected - using mock vLLM (fallback)")
        return True
    if not CUDA_AVAILABLE:
        logger.debug("CUDA not available - using mock vLLM (fallback)")
        return True
    if not VLLM_AVAILABLE:
        logger.debug("vLLM not installed - using mock vLLM (fallback)")
        return True
    return False


# Log platform info at module load
MODE = get_mode()
USE_MOCK_VLLM = should_use_mock_vllm()

logger.info(f"Platform: {SYSTEM} ({MACHINE})")
logger.info(f"Mode: {MODE}")
logger.info(f"VLLM available: {VLLM_AVAILABLE}")
logger.info(f"CUDA available: {CUDA_AVAILABLE}")
logger.info(f"Using mock vLLM: {USE_MOCK_VLLM}")
