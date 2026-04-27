"""vLLM initialization with proper CUDA/multiprocessing handling."""

from __future__ import annotations

import logging
import multiprocessing
import sys
from typing import Optional

logger = logging.getLogger(__name__)


def ensure_spawn_method() -> str:
    """Ensure multiprocessing uses 'spawn' method for CUDA safety.

    Returns:
        The current multiprocessing start method.

    Raises:
        RuntimeError: If spawn method cannot be set.
    """
    try:
        # Check current method
        current = multiprocessing.get_start_method()
        if current == "spawn":
            logger.info("✓ Multiprocessing already using 'spawn' method")
            return current

        # Try to set spawn
        multiprocessing.set_start_method("spawn", force=True)
        logger.info("✓ Set multiprocessing to 'spawn' method for CUDA safety")
        return "spawn"
    except RuntimeError as e:
        logger.error("Failed to set spawn method: %s", e)
        # Try to get current method for logging
        try:
            current = multiprocessing.get_start_method()
            logger.warning("Current method: %s (may cause CUDA issues)", current)
        except:
            pass
        raise


def initialize_vllm_engine(
    model: str,
    gpu_memory_utilization: float = 0.7,
    max_model_len: int = 4096,
    max_num_seqs: int = 256,
    tensor_parallel_size: int = 1,
    quantization: Optional[str] = None,
    dtype: str = "auto",
) -> Optional:
    """Initialize vLLM AsyncLLMEngine with proper multiprocessing setup.

    This function ensures:
    1. Spawn method is set BEFORE any CUDA initialization
    2. AsyncEngineArgs uses correct parameters
    3. Proper error handling for initialization failures

    Args:
        model: Model name or path
        gpu_memory_utilization: GPU memory fraction
        max_model_len: Maximum model length
        max_num_seqs: Maximum concurrent sequences
        tensor_parallel_size: Number of GPUs for tensor parallelism
        quantization: Quantization type (awq, gptq, etc.)
        dtype: Data type (auto, float16, bfloat16)

    Returns:
        AsyncLLMEngine instance or None if initialization fails

    Raises:
        RuntimeError: If spawn method cannot be set or engine fails
    """
    # Ensure spawn method is set FIRST
    ensure_spawn_method()

    # Now import vLLM components
    try:
        from app.vllm_imports import AsyncEngineArgs, AsyncLLMEngine

        logger.info("Initializing vLLM AsyncLLMEngine for model: %s", model)

        # Create engine args
        engine_args = AsyncEngineArgs(
            model=model,
            gpu_memory_utilization=gpu_memory_utilization,
            max_model_len=max_model_len,
            max_num_seqs=max_num_seqs,
            tensor_parallel_size=tensor_parallel_size,
            quantization=quantization,
            dtype=dtype,
            trust_remote_code=True,
            enable_log_requests=False,
        )

        logger.info("AsyncEngineArgs created, initializing engine...")

        # Initialize engine
        # Note: from_engine_args is async in real vLLM, sync in mock
        engine = AsyncLLMEngine.from_engine_args(engine_args)

        # Check if it's a coroutine (real vLLM)
        if hasattr(engine, "__await__"):
            raise RuntimeError(
                "vLLM's AsyncLLMEngine.from_engine_args() returned a coroutine. "
                "This must be awaited in an async context. "
                "Use the lifespan context manager in app/main.py for initialization."
            )

        logger.info("✓ vLLM AsyncLLMEngine initialized successfully")
        return engine

    except Exception as e:
        logger.error("Failed to initialize vLLM engine: %s", e)
        logger.error("Debugging info:")
        logger.error("  - Python version: %s", sys.version)
        logger.error("  - Multiprocessing method: %s", multiprocessing.get_start_method())
        logger.error("  - Model: %s", model)
        logger.error("")
        logger.error("Common solutions:")
        logger.error("  1. Verify CUDA is installed: nvidia-smi")
        logger.error("  2. Verify vLLM installation: python -c 'import vllm'")
        logger.error("  3. Check model exists: huggingface-cli repo info <model>")
        logger.error("  4. Try smaller model for testing")
        raise
