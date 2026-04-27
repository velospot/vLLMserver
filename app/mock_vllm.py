"""Mock vLLM for development/testing without GPU.

This module provides mock implementations of vLLM classes for environments
where CUDA/GPU is not available (e.g., macOS development, testing).

In production (Linux + GPU), real vLLM will be imported instead.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, AsyncGenerator, List, Optional


@dataclass
class SamplingParams:
    """Mock SamplingParams matching vLLM API."""

    temperature: float = 0.7
    top_p: float = 0.9
    max_tokens: int = 512
    stop: Optional[List[str]] = None
    presence_penalty: float = 0.0
    frequency_penalty: float = 0.0
    seed: Optional[int] = None


@dataclass
class PoolingParams:
    """Mock PoolingParams for embeddings."""

    pass


@dataclass
class TokenOutput:
    """Mock token output."""

    token_id: int


@dataclass
class RequestOutput:
    """Mock RequestOutput from generation."""

    request_id: str
    prompt: str
    outputs: list

    @property
    def token_ids(self) -> List[int]:
        """Return mock token IDs."""
        return [1, 2, 3, 4, 5]


@dataclass
class Output:
    """Mock single output from generation."""

    text: str
    token_ids: List[int]


@dataclass
class EmbeddingOutput:
    """Mock embedding output."""

    embedding: list


@dataclass
class PoolingRequestOutput:
    """Mock pooling request output for embeddings."""

    embedding: list


@dataclass
class EmbeddingRequestOutput:
    """Mock embedding request output."""

    request_id: str
    outputs: PoolingRequestOutput


class AsyncEngineArgs:
    """Mock AsyncEngineArgs."""

    def __init__(
        self,
        model: str,
        gpu_memory_utilization: float = 0.7,
        max_model_len: int = 4096,
        max_num_seqs: int = 256,
        tensor_parallel_size: int = 1,
        quantization: Optional[str] = None,
        dtype: str = "auto",
        task: str = "generate",
        trust_remote_code: bool = False,
        disable_log_requests: bool = False,
        **kwargs,
    ) -> None:
        self.model = model
        self.gpu_memory_utilization = gpu_memory_utilization
        self.max_model_len = max_model_len
        self.max_num_seqs = max_num_seqs
        self.tensor_parallel_size = tensor_parallel_size
        self.quantization = quantization
        self.dtype = dtype
        self.task = task
        self.trust_remote_code = trust_remote_code
        self.disable_log_requests = disable_log_requests


class AsyncLLMEngine:
    """Mock AsyncLLMEngine for development."""

    def __init__(self, args: AsyncEngineArgs) -> None:
        self.args = args
        self.model_name = args.model

    @classmethod
    def from_engine_args(cls, engine_args: AsyncEngineArgs) -> AsyncLLMEngine:
        """Create engine from args (not async in mock)."""
        return cls(engine_args)

    async def generate(
        self,
        prompt: str,
        sampling_params: SamplingParams,
        request_id: str,
    ) -> AsyncGenerator[RequestOutput, None]:
        """Mock generation - yields token-by-token outputs."""
        # Simulate token-by-token generation
        tokens = ["Mock", " ", "response", " ", "from", " ", "LLM"]
        full_text = ""

        for token in tokens:
            full_text += token
            output = Output(text=full_text, token_ids=[1, 2, 3])
            yield RequestOutput(
                request_id=request_id,
                prompt=prompt,
                outputs=[output],
            )

    async def encode(
        self,
        prompt: str,
        pooling_params: PoolingParams,
        request_id: str,
    ) -> AsyncGenerator[EmbeddingRequestOutput, None]:
        """Mock embeddings - returns 768-dim vector."""
        # Return mock embedding
        mock_embedding = [0.1] * 768
        yield EmbeddingRequestOutput(
            request_id=request_id,
            outputs=PoolingRequestOutput(embedding=mock_embedding),
        )
