from __future__ import annotations

import json
import logging
import time
import uuid
from typing import AsyncIterator, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.auth import APIKeyValidator
from app.metrics import RequestTimer, requests_total, tokens_generated, tokens_received
from app.models import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionStreamResponse,
    ChatMessage,
    Choice,
    DeltaMessage,
    StreamChoice,
    Usage,
)
from app.rate_limit import limiter
from app.services.llm import LLMService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Chat"])


def get_llm_service(request: Request) -> LLMService:
    service: Optional[LLMService] = getattr(request.app.state, "llm_service", None)
    if service is None:
        raise HTTPException(status_code=503, detail="Chat model not loaded")
    return service


@router.post(
    "/chat/completions",
    response_model=None,
    summary="Create a chat completion",
    response_description="OpenAI-compatible chat completion response",
)
async def create_chat_completion(
    request: ChatCompletionRequest,
    http_request: Request,
    service: LLMService = Depends(get_llm_service),
):
    # Authentication
    api_key = http_request.headers.get("X-API-Key")
    if api_key:
        tier = APIKeyValidator.validate(api_key)
    else:
        api_key = "anonymous"
        tier = "demo"

    # Estimate tokens for rate limiting
    estimated_prompt_tokens = sum(len(m.content.split()) for m in request.messages) + 50
    estimated_completion_tokens = request.max_tokens

    # Rate limiting
    allowed, error_msg = limiter.check_and_record(
        api_key, estimated_prompt_tokens, estimated_completion_tokens
    )
    if not allowed:
        logger.warning(f"Rate limit: {error_msg} for {api_key}")
        raise HTTPException(status_code=429, detail=error_msg)

    stop: Optional[List[str]] = (
        [request.stop] if isinstance(request.stop, str) else request.stop
    )

    # Track metrics
    timer = RequestTimer("chat_completions", service.model_name)

    if request.stream:
        return StreamingResponse(
            _stream_response(request, service, stop, timer, api_key),
            media_type="text/event-stream",
            headers={"X-Accel-Buffering": "no"},
        )

    with timer:
        try:
            text, prompt_tokens, completion_tokens = await service.generate(
                messages=request.messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                top_p=request.top_p,
                stop=stop,
                presence_penalty=request.presence_penalty,
                frequency_penalty=request.frequency_penalty,
                seed=request.seed,
            )
        except Exception as exc:
            logger.exception("Generation failed")
            requests_total.labels(endpoint="chat_completions", status="error").inc()
            raise HTTPException(status_code=500, detail=str(exc))

        # Record metrics
        tokens_received.labels(model=service.model_name).inc(prompt_tokens)
        tokens_generated.labels(model=service.model_name).inc(completion_tokens)

    return ChatCompletionResponse(
        id=f"chatcmpl-{uuid.uuid4().hex}",
        created=int(time.time()),
        model=service.model_name,
        choices=[
            Choice(
                index=0,
                message=ChatMessage(role="assistant", content=text),
                finish_reason="stop",
            )
        ],
        usage=Usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        ),
    )


async def _stream_response(
    request: ChatCompletionRequest,
    service: LLMService,
    stop: Optional[List[str]],
    timer: RequestTimer,
    api_key: str,
) -> AsyncIterator[str]:
    completion_id = f"chatcmpl-{uuid.uuid4().hex}"
    created = int(time.time())

    with timer:
        # Initial chunk: role
        first = ChatCompletionStreamResponse(
            id=completion_id,
            created=created,
            model=service.model_name,
            choices=[StreamChoice(index=0, delta=DeltaMessage(role="assistant"))],
        )
        yield f"data: {first.model_dump_json()}\n\n"

        completion_tokens = 0
        prompt_tokens = sum(len(m.content.split()) for m in request.messages) + 50

        try:
            async for delta in service.generate_stream(
                messages=request.messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                top_p=request.top_p,
                stop=stop,
                presence_penalty=request.presence_penalty,
                frequency_penalty=request.frequency_penalty,
                seed=request.seed,
            ):
                completion_tokens += len(delta.split())
                chunk = ChatCompletionStreamResponse(
                    id=completion_id,
                    created=created,
                    model=service.model_name,
                    choices=[StreamChoice(index=0, delta=DeltaMessage(content=delta))],
                )
                yield f"data: {chunk.model_dump_json()}\n\n"
        except Exception:
            logger.exception("Streaming generation failed")
            requests_total.labels(endpoint="chat_completions", status="error").inc()
            raise

        # Record metrics
        tokens_received.labels(model=service.model_name).inc(prompt_tokens)
        tokens_generated.labels(model=service.model_name).inc(completion_tokens)

    # Final chunk: finish_reason
    final = ChatCompletionStreamResponse(
        id=completion_id,
        created=created,
        model=service.model_name,
        choices=[StreamChoice(index=0, delta=DeltaMessage(), finish_reason="stop")],
    )
    yield f"data: {final.model_dump_json()}\n\n"
    yield "data: [DONE]\n\n"
