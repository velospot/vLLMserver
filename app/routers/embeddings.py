from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from app.models import EmbeddingData, EmbeddingRequest, EmbeddingResponse, EmbeddingUsage
from app.services.embedding import EmbeddingService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Embeddings"])


def get_embedding_service(request: Request) -> EmbeddingService:
    service: Optional[EmbeddingService] = getattr(request.app.state, "embedding_service", None)
    if service is None:
        raise HTTPException(status_code=503, detail="Embedding model not loaded")
    return service


@router.post(
    "/embeddings",
    response_model=EmbeddingResponse,
    summary="Create text embeddings",
    response_description="OpenAI-compatible embeddings response",
)
async def create_embeddings(
    request: EmbeddingRequest,
    service: EmbeddingService = Depends(get_embedding_service),
) -> EmbeddingResponse:
    texts: List[str] = (
        [request.input] if isinstance(request.input, str) else list(request.input)
    )

    try:
        vectors = await service.embed(texts)
    except Exception as exc:
        logger.exception("Embedding failed")
        raise HTTPException(status_code=500, detail=str(exc))

    # Approximate token count from whitespace-split word count
    total_tokens = sum(len(t.split()) for t in texts)

    return EmbeddingResponse(
        data=[EmbeddingData(index=i, embedding=vec) for i, vec in enumerate(vectors)],
        model=service.model_name,
        usage=EmbeddingUsage(prompt_tokens=total_tokens, total_tokens=total_tokens),
    )
