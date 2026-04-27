from __future__ import annotations

import asyncio
import logging
import uuid
from typing import List

from app.vllm_imports import AsyncEngineArgs, AsyncLLMEngine, PoolingParams

logger = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(
        self,
        model: str,
        gpu_memory_utilization: float = 0.2,
        max_model_len: int = 512,
        tensor_parallel_size: int = 1,
    ) -> None:
        engine_args = AsyncEngineArgs(
            model=model,
            gpu_memory_utilization=gpu_memory_utilization,
            max_model_len=max_model_len,
            tensor_parallel_size=tensor_parallel_size,
            task="embed",
            trust_remote_code=True,
            enable_log_requests=False,
        )
        self.engine = AsyncLLMEngine.from_engine_args(engine_args)
        self.model_name = model

    async def _embed_one(self, text: str) -> List[float]:
        request_id = str(uuid.uuid4())
        pooling_params = PoolingParams()
        final_output = None
        async for output in self.engine.encode(text, pooling_params, request_id):
            final_output = output
        raw = final_output.outputs.embedding
        return raw.tolist() if hasattr(raw, "tolist") else list(raw)

    async def embed(self, texts: List[str]) -> List[List[float]]:
        return await asyncio.gather(*[self._embed_one(t) for t in texts])
