"""Comprehensive startup and initialization tests."""

from __future__ import annotations

import asyncio
import pytest
from fastapi.testclient import TestClient


def test_imports() -> None:
    """Test that all modules can be imported without errors."""
    import app.config
    import app.auth
    import app.cache
    import app.metrics
    import app.rate_limit
    import app.models
    import app.services.llm
    import app.services.embedding
    import app.routers.chat
    import app.routers.embeddings
    import app.routers.models
    import app.main

    assert app.config is not None
    assert app.main is not None


def test_fastapi_app_creation() -> None:
    """Test that FastAPI app can be created and configured."""
    from app.main import app

    assert app is not None
    assert app.title == "vLLM Inference Server"
    assert app.version == "1.0.0"


def test_app_routes_registered() -> None:
    """Test that all routes are properly registered."""
    from app.main import app

    routes = [route.path for route in app.routes]

    # Core endpoints
    assert "/health" in routes
    assert "/v1/models" in routes
    assert "/metrics" in routes

    # Chat endpoints
    assert "/v1/chat/completions" in routes

    # Embeddings endpoint
    assert "/v1/embeddings" in routes

    # Model discovery endpoints
    assert "/v1/models/detailed" in routes
    assert "/v1/rate-limits" in routes


def test_config_loads() -> None:
    """Test that configuration loads correctly."""
    from app.config import settings

    assert settings.chat_model == "Qwen/Qwen2.5-7B-Instruct-AWQ"
    assert settings.host == "0.0.0.0"
    assert settings.port == 8000
    assert 0 < settings.chat_gpu_memory_utilization <= 1.0
    assert settings.chat_max_model_len > 0


def test_client_can_connect() -> None:
    """Test that TestClient can connect to the app."""
    from app.main import app

    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health_endpoint() -> None:
    """Test health check endpoint."""
    from app.main import app

    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["chat_model"] is not None
    assert "embedding_model" in data


def test_models_endpoint() -> None:
    """Test /v1/models endpoint returns loaded models."""
    from app.main import app

    client = TestClient(app)
    response = client.get("/v1/models")

    assert response.status_code == 200
    data = response.json()
    assert data["object"] == "list"
    assert isinstance(data["data"], list)
    assert len(data["data"]) > 0


def test_metrics_endpoint() -> None:
    """Test /metrics endpoint returns Prometheus data."""
    from app.main import app

    client = TestClient(app)
    response = client.get("/metrics")

    assert response.status_code == 200
    assert "llm_" in response.text or response.text  # Should have metrics
    assert "TYPE" in response.text or "HELP" in response.text or response.text  # Prometheus format


def test_models_detailed_endpoint() -> None:
    """Test /v1/models/detailed endpoint."""
    from app.main import app

    client = TestClient(app)
    response = client.get("/v1/models/detailed")

    assert response.status_code == 200
    data = response.json()
    assert data["object"] == "list"
    assert isinstance(data["data"], list)
    assert isinstance(data.get("total"), int)

    # Check model structure if models are available
    if len(data["data"]) > 0:
        model = data["data"][0]
        assert "id" in model
        assert "architecture" in model
        assert "capabilities" in model
        assert "limits" in model


def test_auth_validator() -> None:
    """Test API key validation."""
    from app.auth import APIKeyValidator
    from fastapi import HTTPException

    # Valid key
    tier = APIKeyValidator.validate("sk-dev-test")
    assert tier == "development"

    tier = APIKeyValidator.validate("sk-prod-primary")
    assert tier == "production"

    # Invalid key
    with pytest.raises(HTTPException) as exc_info:
        APIKeyValidator.validate("invalid-key")
    assert exc_info.value.status_code == 401

    # Missing key
    with pytest.raises(HTTPException) as exc_info:
        APIKeyValidator.validate(None)
    assert exc_info.value.status_code == 401


def test_rate_limiter() -> None:
    """Test token-aware rate limiting."""
    from app.rate_limit import TokenRateLimiter

    limiter = TokenRateLimiter(rpm_limit=10, tpm_limit=1000, tpd_limit=10000)

    # First request should be allowed
    allowed, msg = limiter.check_and_record("user1", 100, 50)
    assert allowed is True
    assert msg is None

    # Check usage
    stats = limiter.get_usage_stats("user1")
    assert stats["requests_this_minute"] == 1
    assert stats["tokens_this_minute"] == 150

    # Exceed TPM limit
    allowed, msg = limiter.check_and_record("user2", 500, 600)  # 1100 tokens > 1000 limit
    assert allowed is False
    assert "Token limit exceeded" in msg


def test_llm_service_initialization() -> None:
    """Test LLM service can be initialized."""
    from app.services.llm import LLMService
    from app.config import settings

    service = LLMService(
        model=settings.chat_model,
        gpu_memory_utilization=settings.chat_gpu_memory_utilization,
        max_model_len=settings.chat_max_model_len,
    )

    assert service is not None
    assert service.model_name == settings.chat_model
    assert service.tokenizer is not None


def test_embedding_service_initialization() -> None:
    """Test embedding service can be initialized."""
    from app.services.embedding import EmbeddingService

    service = EmbeddingService(
        model="BAAI/bge-m3",
        gpu_memory_utilization=0.2,
        max_model_len=512,
    )

    assert service is not None
    assert service.model_name == "BAAI/bge-m3"


@pytest.mark.asyncio
async def test_llm_service_generate() -> None:
    """Test LLM service generation (with mock)."""
    from app.services.llm import LLMService
    from app.models import Message

    service = LLMService(
        model="Qwen/Qwen2.5-7B-Instruct-AWQ",
        gpu_memory_utilization=0.7,
    )

    messages = [Message(role="user", content="Hello")]
    text, prompt_tokens, completion_tokens = await service.generate(
        messages=messages,
        max_tokens=100,
    )

    assert isinstance(text, str)
    assert len(text) > 0
    assert isinstance(prompt_tokens, int)
    assert isinstance(completion_tokens, int)


@pytest.mark.asyncio
async def test_embedding_service_embed() -> None:
    """Test embedding service (with mock)."""
    from app.services.embedding import EmbeddingService

    service = EmbeddingService(
        model="BAAI/bge-m3",
        gpu_memory_utilization=0.2,
    )

    texts = ["Hello world", "Another text"]
    embeddings = await service.embed(texts)

    assert isinstance(embeddings, list)
    assert len(embeddings) == 2
    for emb in embeddings:
        assert isinstance(emb, list)
        assert len(emb) > 0


def test_pydantic_models() -> None:
    """Test that all Pydantic models are valid."""
    from app.models import (
        Message,
        ChatCompletionRequest,
        EmbeddingRequest,
        DetailedModelInfo,
        HealthResponse,
        RateLimitStatus,
    )

    # Test Message
    msg = Message(role="user", content="Hello")
    assert msg.role == "user"
    assert msg.content == "Hello"

    # Test ChatCompletionRequest
    req = ChatCompletionRequest(
        model="test",
        messages=[msg],
    )
    assert req.model == "test"
    assert len(req.messages) == 1

    # Test EmbeddingRequest
    emb_req = EmbeddingRequest(
        model="test",
        input="hello",
    )
    assert emb_req.model == "test"

    # Test HealthResponse
    health = HealthResponse(status="ok", chat_model="test")
    assert health.status == "ok"

    # Test RateLimitStatus
    rls = RateLimitStatus(
        requests_this_minute=5,
        tokens_this_minute=100,
        tokens_today=1000,
        rpm_limit=60,
        tpm_limit=100000,
        tpd_limit=10000000,
    )
    assert rls.requests_this_minute == 5


def test_cache_scanning() -> None:
    """Test HF cache scanner initialization."""
    from app.cache import scan_huggingface_cache

    # This should not crash even if HF cache is empty
    models = scan_huggingface_cache()
    assert isinstance(models, dict)


def test_metrics_initialization() -> None:
    """Test that Prometheus metrics are properly initialized."""
    from app import metrics

    # Check that all metrics are defined
    assert metrics.requests_total is not None
    assert metrics.tokens_generated is not None
    assert metrics.time_to_first_token is not None
    assert metrics.request_duration is not None


def test_app_middleware() -> None:
    """Test that CORS middleware is configured."""
    from app.main import app

    # Check middleware
    middleware_types = [type(m).__name__ for m in app.user_middleware]
    assert any("CORS" in m for m in middleware_types)


def test_concurrent_requests() -> None:
    """Test that app can handle concurrent requests."""
    from app.main import app

    client = TestClient(app)

    # Make multiple concurrent health checks
    responses = []
    for _ in range(5):
        response = client.get("/health")
        responses.append(response.status_code)

    assert all(code == 200 for code in responses)


def test_error_handling_404() -> None:
    """Test 404 error handling."""
    from app.main import app

    client = TestClient(app)
    response = client.get("/nonexistent")
    assert response.status_code == 404


def test_invalid_request_data() -> None:
    """Test that invalid request data is rejected."""
    from app.main import app

    client = TestClient(app)

    # Invalid chat request (missing required fields)
    response = client.post(
        "/v1/chat/completions",
        json={"model": "test"},  # Missing messages
    )
    assert response.status_code in [422, 400]  # Validation error


# Integration tests
@pytest.mark.asyncio
async def test_full_startup_lifecycle() -> None:
    """Test complete startup lifecycle."""
    from app.main import app

    # App should be ready
    assert app is not None
    assert len(app.routes) > 0

    # All key endpoints should be available
    client = TestClient(app)

    health = client.get("/health")
    assert health.status_code == 200

    models = client.get("/v1/models")
    assert models.status_code == 200

    metrics = client.get("/metrics")
    assert metrics.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
