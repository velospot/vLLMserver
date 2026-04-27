from __future__ import annotations

import logging
import uuid
from typing import AsyncIterator, List, Optional

from transformers import AutoTokenizer

from app.vllm_imports import AsyncEngineArgs, AsyncLLMEngine, SamplingParams

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(
        self,
        model: str,
        gpu_memory_utilization: float = 0.7,
        max_model_len: int = 4096,
        max_num_seqs: int = 256,
        tensor_parallel_size: int = 1,
        quantization: Optional[str] = None,
        dtype: str = "auto",
    ) -> None:
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
        # Note: from_engine_args is async in real vLLM, but we call it synchronously
        # The real vLLM version will need async initialization at server start
        from_engine_args = AsyncLLMEngine.from_engine_args(engine_args)
        # If it's a coroutine (real vLLM), it should be handled by caller
        # If it's an object (mock vLLM), use it directly
        if hasattr(from_engine_args, '__await__'):
            raise RuntimeError(
                "vLLM's AsyncLLMEngine.from_engine_args() is async. "
                "Use app.main.lifespan() context manager to initialize models."
            )
        self.engine = from_engine_args
        self.model_name = model

        # Try to load tokenizer; fall back to mock if model doesn't exist
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model, trust_remote_code=True)
        except Exception as e:
            logger.warning(f"Could not load tokenizer for {model}: {e}. Using fallback.")
            self.tokenizer = None

    def _build_prompt(self, messages: list) -> str:
        formatted = [{"role": m.role, "content": m.content} for m in messages]
        if self.tokenizer is None:
            # Fallback: simple prompt formatting
            return "\n".join([f"{m.get('role', 'user')}: {m.get('content', '')}" for m in formatted])
        return self.tokenizer.apply_chat_template(
            formatted, tokenize=False, add_generation_prompt=True
        )

    def _sampling_params(
        self,
        temperature: float,
        max_tokens: int,
        top_p: float,
        stop: Optional[List[str]],
        presence_penalty: float,
        frequency_penalty: float,
        seed: Optional[int],
    ) -> SamplingParams:
        return SamplingParams(
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            stop=stop,
            presence_penalty=presence_penalty,
            frequency_penalty=frequency_penalty,
            seed=seed,
        )

    async def generate(
        self,
        messages: list,
        temperature: float = 0.7,
        max_tokens: int = 512,
        top_p: float = 0.9,
        stop: Optional[List[str]] = None,
        presence_penalty: float = 0.0,
        frequency_penalty: float = 0.0,
        seed: Optional[int] = None,
    ) -> tuple[str, int, int]:
        prompt = self._build_prompt(messages)
        params = self._sampling_params(
            temperature, max_tokens, top_p, stop, presence_penalty, frequency_penalty, seed
        )
        request_id = str(uuid.uuid4())
        # Estimate token count if tokenizer not available
        if self.tokenizer is None:
            prompt_tokens = len(prompt.split())
        else:
            prompt_tokens = len(self.tokenizer.encode(prompt))

        final_output = None
        async for output in self.engine.generate(prompt, params, request_id):
            final_output = output

        text = final_output.outputs[0].text
        completion_tokens = len(final_output.outputs[0].token_ids)
        return text, prompt_tokens, completion_tokens

    async def generate_stream(
        self,
        messages: list,
        temperature: float = 0.7,
        max_tokens: int = 512,
        top_p: float = 0.9,
        stop: Optional[List[str]] = None,
        presence_penalty: float = 0.0,
        frequency_penalty: float = 0.0,
        seed: Optional[int] = None,
    ) -> AsyncIterator[str]:
        prompt = self._build_prompt(messages)
        params = self._sampling_params(
            temperature, max_tokens, top_p, stop, presence_penalty, frequency_penalty, seed
        )
        request_id = str(uuid.uuid4())
        previous_text = ""

        try:
            async for output in self.engine.generate(prompt, params, request_id):
                new_text = output.outputs[0].text
                delta = new_text[len(previous_text):]
                previous_text = new_text
                if delta:
                    yield delta
        except RuntimeError as e:
            logger.error(f"Stream generation failed: {e}")
