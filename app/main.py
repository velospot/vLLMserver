from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import generate_latest, REGISTRY
from fastapi.responses import Response

from app.config import settings
from app.models import HealthResponse, ModelInfo, ModelsResponse
from app.platform_detect import MODE, USE_MOCK_VLLM, CUDA_AVAILABLE, SYSTEM
from app.routers import chat, embeddings, models

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage model loading and cleanup lifecycle."""
    # Log startup info
    logger.info("=" * 70)
    logger.info("vLLM Inference Server Starting")
    logger.info("=" * 70)
    logger.info("Platform: %s | Mode: %s | CUDA: %s | Mock vLLM: %s",
                SYSTEM, MODE, CUDA_AVAILABLE, USE_MOCK_VLLM)
    if USE_MOCK_VLLM:
        logger.warning("⚠️  Using mock vLLM - suitable for testing/development only")
        logger.warning("    For production GPU inference, install vLLM on Linux with CUDA")
    logger.info("=" * 70)

    # ── Load chat model ────────────────────────────────────────────────────────
    try:
        logger.info("Loading chat model: %s", settings.chat_model)
        from app.services.llm import LLMService

        app.state.llm_service = LLMService(
            model=settings.chat_model,
            gpu_memory_utilization=settings.chat_gpu_memory_utilization,
            max_model_len=settings.chat_max_model_len,
            max_num_seqs=settings.chat_max_num_seqs,
            tensor_parallel_size=settings.chat_tensor_parallel_size,
            quantization=settings.chat_quantization,
            dtype=settings.chat_dtype,
        )
        logger.info("Chat model ready: %s", settings.chat_model)
    except Exception as e:
        logger.error("Failed to load chat model: %s", e)
        app.state.llm_service = None
        raise

    # ── Load embedding model (optional) ────────────────────────────────────────
    app.state.embedding_service = None
    if settings.embedding_model:
        try:
            logger.info("Loading embedding model: %s", settings.embedding_model)
            from app.services.embedding import EmbeddingService

            app.state.embedding_service = EmbeddingService(
                model=settings.embedding_model,
                gpu_memory_utilization=settings.embedding_gpu_memory_utilization,
                max_model_len=settings.embedding_max_model_len,
                tensor_parallel_size=settings.embedding_tensor_parallel_size,
            )
            logger.info("Embedding model ready: %s", settings.embedding_model)
        except Exception as e:
            logger.warning("Failed to load embedding model: %s", e)
            app.state.embedding_service = None

    yield

    logger.info("Server shutting down")


app = FastAPI(
    title="vLLM Inference Server",
    description=(
        "Production-ready vLLM inference server with OpenAI-compatible endpoints "
        "for chat completion and text embeddings."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router, prefix="/v1")
app.include_router(embeddings.router, prefix="/v1")
app.include_router(models.router, prefix="/v1")


@app.get("/health", response_model=HealthResponse, tags=["Operations"])
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        chat_model=settings.chat_model,
        embedding_model=settings.embedding_model,
        mode=MODE,
        using_mock_vllm=USE_MOCK_VLLM,
    )


@app.get("/system", response_model=dict, tags=["Operations"])
async def system_info() -> dict:
    """Get system and GPU information."""
    from app.models import SystemInfo

    return SystemInfo(
        platform=SYSTEM,
        mode=MODE,
        cuda_available=CUDA_AVAILABLE,
        using_mock_vllm=USE_MOCK_VLLM,
        chat_model=settings.chat_model,
        embedding_model=settings.embedding_model,
    ).model_dump()


@app.get("/v1/models", response_model=ModelsResponse, tags=["Operations"])
async def list_models() -> ModelsResponse:
    created = int(time.time())
    models = []
    if getattr(app.state, "llm_service", None):
        models.append(ModelInfo(id=settings.chat_model, created=created))
    if getattr(app.state, "embedding_service", None):
        models.append(ModelInfo(id=settings.embedding_model, created=created))
    return ModelsResponse(data=models)


@app.get("/metrics", tags=["Observability"])
async def get_metrics() -> Response:
    """Prometheus metrics endpoint."""
    return Response(
        content=generate_latest(REGISTRY),
        media_type="text/plain; charset=utf-8",
    )
