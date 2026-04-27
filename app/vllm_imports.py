"""Conditional imports: real vLLM on GPU, mock vLLM on CPU/macOS."""

from __future__ import annotations

from app.platform_detect import USE_MOCK_VLLM

if USE_MOCK_VLLM:
    from app.mock_vllm import (
        AsyncEngineArgs,
        AsyncLLMEngine,
        PoolingParams,
        SamplingParams,
    )
else:
    from vllm import AsyncEngineArgs, AsyncLLMEngine, PoolingParams, SamplingParams

__all__ = [
    "AsyncEngineArgs",
    "AsyncLLMEngine",
    "PoolingParams",
    "SamplingParams",
]
