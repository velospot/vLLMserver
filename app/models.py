from __future__ import annotations

from typing import List, Literal, Optional, Union

from pydantic import BaseModel, Field


# ── Shared ────────────────────────────────────────────────────────────────────

class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


# ── Chat completions ───────────────────────────────────────────────────────────

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[Message]
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=512, ge=1, le=32768)
    top_p: float = Field(default=0.9, ge=0.0, le=1.0)
    stream: bool = False
    stop: Optional[Union[str, List[str]]] = None
    presence_penalty: float = Field(default=0.0, ge=-2.0, le=2.0)
    frequency_penalty: float = Field(default=0.0, ge=-2.0, le=2.0)
    seed: Optional[int] = None


class ChatMessage(BaseModel):
    role: str = "assistant"
    content: str


class Choice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: str


class DeltaMessage(BaseModel):
    role: Optional[str] = None
    content: Optional[str] = None


class StreamChoice(BaseModel):
    index: int
    delta: DeltaMessage
    finish_reason: Optional[str] = None


class Usage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Choice]
    usage: Usage


class ChatCompletionStreamResponse(BaseModel):
    id: str
    object: str = "chat.completion.chunk"
    created: int
    model: str
    choices: List[StreamChoice]


# ── Embeddings ─────────────────────────────────────────────────────────────────

class EmbeddingRequest(BaseModel):
    model: str
    input: Union[str, List[str]]
    encoding_format: Literal["float", "base64"] = "float"


class EmbeddingData(BaseModel):
    object: str = "embedding"
    index: int
    embedding: List[float]


class EmbeddingUsage(BaseModel):
    prompt_tokens: int
    total_tokens: int


class EmbeddingResponse(BaseModel):
    object: str = "list"
    data: List[EmbeddingData]
    model: str
    usage: EmbeddingUsage


# ── Model list ─────────────────────────────────────────────────────────────────

class ModelInfo(BaseModel):
    id: str
    object: str = "model"
    created: int
    owned_by: str = "vllmserver"


class ModelsResponse(BaseModel):
    object: str = "list"
    data: List[ModelInfo]


# ── Health ─────────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    chat_model: Optional[str] = None
    embedding_model: Optional[str] = None
    mode: Optional[str] = None
    using_mock_vllm: Optional[bool] = None


class SystemInfo(BaseModel):
    platform: str
    mode: Literal["production", "development"]
    cuda_available: bool
    using_mock_vllm: bool
    chat_model: Optional[str] = None
    embedding_model: Optional[str] = None


# ── Detailed model info ────────────────────────────────────────────────────────

class ModelCapabilities(BaseModel):
    context_length: int = Field(description="Maximum context window in tokens")
    max_completion_tokens: int = Field(description="Maximum tokens that can be generated")
    supports_streaming: bool = True
    supports_system_prompt: bool = True


class ModelLimits(BaseModel):
    rpm: int = Field(description="Requests per minute")
    tpm: int = Field(description="Tokens per minute")
    tpd: int = Field(description="Tokens per day")
    max_batch_size: int = Field(description="Maximum concurrent requests in batch")


class DetailedModelInfo(BaseModel):
    id: str = Field(description="HuggingFace model ID")
    object: str = "model"
    created: int
    owned_by: str = "vllmserver"
    architecture: str = Field(description="Model architecture (e.g., LlamaForCausalLM)")
    parameters: int = Field(description="Approximate number of parameters")
    size_gb: float = Field(description="Model size on disk in gigabytes")
    quantization: Optional[str] = Field(
        None, description="Quantization format (awq, gptq, int8, etc.)"
    )
    capabilities: ModelCapabilities
    limits: ModelLimits
    tags: List[str] = Field(default_factory=list, description="Tags (quantization, type, etc.)")


class DetailedModelsResponse(BaseModel):
    object: str = "list"
    data: List[DetailedModelInfo]
    total: int


class RateLimitStatus(BaseModel):
    requests_this_minute: int
    tokens_this_minute: int
    tokens_today: int
    rpm_limit: int
    tpm_limit: int
    tpd_limit: int
