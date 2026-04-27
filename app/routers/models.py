"""Model discovery and metadata endpoints."""

from __future__ import annotations

import logging
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from app.auth import APIKeyValidator
from app.cache import scan_huggingface_cache
from app.config import settings
from app.models import (
    DetailedModelInfo,
    DetailedModelsResponse,
    ModelCapabilities,
    ModelLimits,
    RateLimitStatus,
)
from app.rate_limit import limiter

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Models"])


def get_api_key(request: Request) -> str:
    """Extract and validate API key from request."""
    api_key = request.headers.get("X-API-Key")
    if api_key is None:
        # Allow listing models without auth; require auth for rate limit status
        return "anonymous"
    APIKeyValidator.validate(api_key)
    return api_key


@router.get(
    "/models/detailed",
    response_model=DetailedModelsResponse,
    summary="List all models with detailed specs",
    description="Returns detailed information about all models in the HuggingFace cache, including capabilities and parameter limits",
)
async def list_models_detailed() -> DetailedModelsResponse:
    """Scan HF cache and return detailed model information with specs."""
    hf_models = scan_huggingface_cache()
    created = int(time.time())
    models = []

    # Add loaded models (override HF cache info)
    loaded_models = {settings.chat_model, settings.embedding_model}
    for model_id in loaded_models:
        if model_id is None:
            continue

        # Try to get from HF cache first
        if model_id in hf_models:
            meta = hf_models[model_id]
        else:
            # Create placeholder if not in cache
            from app.cache import ModelMetadata

            meta = ModelMetadata(model_id, 0, [], {})

        # Adjust limits based on model type
        is_chat = model_id == settings.chat_model
        if is_chat:
            context = settings.chat_max_model_len
            limits = ModelLimits(
                rpm=60,
                tpm=100000,
                tpd=10000000,
                max_batch_size=settings.chat_max_num_seqs,
            )
        else:
            context = settings.embedding_max_model_len
            limits = ModelLimits(rpm=100, tpm=1000000, tpd=100000000, max_batch_size=256)

        models.append(
            DetailedModelInfo(
                id=model_id,
                created=created,
                architecture=meta.architecture,
                parameters=meta.num_parameters,
                size_gb=meta.size_gb,
                quantization=meta.quantization_type,
                capabilities=ModelCapabilities(
                    context_length=context,
                    max_completion_tokens=min(4096, context // 2),
                    supports_streaming=is_chat,
                    supports_system_prompt=is_chat,
                ),
                limits=limits,
                tags=meta.tags,
            )
        )

    # Add other cached models (available but not loaded)
    for model_id, meta in hf_models.items():
        if model_id not in loaded_models:
            models.append(
                DetailedModelInfo(
                    id=model_id,
                    created=created,
                    architecture=meta.architecture,
                    parameters=meta.num_parameters,
                    size_gb=meta.size_gb,
                    quantization=meta.quantization_type,
                    capabilities=ModelCapabilities(
                        context_length=meta.context_length,
                        max_completion_tokens=min(4096, meta.context_length // 2),
                        supports_streaming=False,
                        supports_system_prompt=False,
                    ),
                    limits=ModelLimits(rpm=10, tpm=50000, tpd=5000000, max_batch_size=32),
                    tags=meta.tags,
                )
            )

    return DetailedModelsResponse(data=models, total=len(models))


@router.get(
    "/rate-limits",
    response_model=RateLimitStatus,
    summary="Get current rate limit status",
    description="Returns current token and request usage for authenticated user",
)
async def get_rate_limit_status(
    api_key: str = Depends(get_api_key),
) -> RateLimitStatus:
    """Get rate limit statistics for the authenticated user."""
    if api_key == "anonymous":
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Provide X-API-Key header.",
        )

    stats = limiter.get_usage_stats(api_key)
    return RateLimitStatus(**stats)
