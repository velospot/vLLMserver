"""Tests for platform and GPU detection."""

from __future__ import annotations

import pytest


def test_platform_detection() -> None:
    """Test platform detection module loads."""
    from app import platform_detect

    assert platform_detect.SYSTEM in ["Darwin", "Linux", "Windows"]
    assert platform_detect.MACHINE is not None


def test_platform_booleans() -> None:
    """Test platform boolean flags."""
    from app.platform_detect import IS_MACOS, IS_LINUX, IS_WINDOWS, SYSTEM

    # Exactly one should be True
    flags = [IS_MACOS, IS_LINUX, IS_WINDOWS]
    assert sum(flags) == 1, "Exactly one platform flag should be True"

    # Flags should match SYSTEM
    if SYSTEM == "Darwin":
        assert IS_MACOS
    elif SYSTEM == "Linux":
        assert IS_LINUX
    elif SYSTEM == "Windows":
        assert IS_WINDOWS


def test_mock_vllm_fallback_on_macos() -> None:
    """Test that macOS uses mock vLLM."""
    from app.platform_detect import IS_MACOS, USE_MOCK_VLLM

    if IS_MACOS:
        assert USE_MOCK_VLLM is True, "macOS should use mock vLLM"


def test_conditional_imports() -> None:
    """Test that conditional imports work."""
    from app.vllm_imports import AsyncEngineArgs, AsyncLLMEngine, SamplingParams, PoolingParams

    # Should not raise ImportError
    assert AsyncEngineArgs is not None
    assert AsyncLLMEngine is not None
    assert SamplingParams is not None
    assert PoolingParams is not None


def test_mode_detection() -> None:
    """Test mode detection returns valid value."""
    from app.platform_detect import MODE

    assert MODE in ["production", "development"]


def test_mock_vllm_implementations() -> None:
    """Test mock vLLM implementations."""
    from app.mock_vllm import (
        SamplingParams,
        PoolingParams,
        AsyncEngineArgs,
        AsyncLLMEngine,
    )

    # Test SamplingParams
    params = SamplingParams(temperature=0.7, max_tokens=512)
    assert params.temperature == 0.7
    assert params.max_tokens == 512

    # Test PoolingParams
    pool = PoolingParams()
    assert pool is not None

    # Test AsyncEngineArgs
    args = AsyncEngineArgs(
        model="test-model",
        gpu_memory_utilization=0.7,
        max_model_len=4096,
    )
    assert args.model == "test-model"
    assert args.gpu_memory_utilization == 0.7
    assert args.max_model_len == 4096

    # Test AsyncLLMEngine
    engine = AsyncLLMEngine(args)
    assert engine.args == args
    assert engine.model_name == "test-model"


@pytest.mark.asyncio
async def test_mock_engine_generate() -> None:
    """Test mock engine generation."""
    from app.mock_vllm import AsyncLLMEngine, AsyncEngineArgs, SamplingParams

    args = AsyncEngineArgs(model="test-model")
    engine = AsyncLLMEngine(args)
    params = SamplingParams()

    output_count = 0
    async for output in engine.generate("test prompt", params, "req-123"):
        output_count += 1
        assert output.request_id == "req-123"
        assert output.prompt == "test prompt"
        assert len(output.outputs) > 0

    assert output_count > 0, "Should yield at least one output"


@pytest.mark.asyncio
async def test_mock_engine_encode() -> None:
    """Test mock engine embeddings."""
    from app.mock_vllm import AsyncLLMEngine, AsyncEngineArgs, PoolingParams

    args = AsyncEngineArgs(model="test-model")
    engine = AsyncLLMEngine(args)
    params = PoolingParams()

    output_count = 0
    async for output in engine.encode("test text", params, "req-456"):
        output_count += 1
        assert output.request_id == "req-456"
        assert hasattr(output.outputs, "embedding")
        assert len(output.outputs.embedding) > 0

    assert output_count > 0, "Should yield at least one output"


def test_health_endpoint_shows_mode() -> None:
    """Test that health endpoint shows mode info."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert "mode" in data
    assert data["mode"] in ["production", "development"]
    assert "using_mock_vllm" in data
    assert isinstance(data["using_mock_vllm"], bool)


def test_system_endpoint() -> None:
    """Test /system endpoint returns platform info."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    response = client.get("/system")

    assert response.status_code == 200
    data = response.json()
    assert "platform" in data
    assert "mode" in data
    assert "cuda_available" in data
    assert "using_mock_vllm" in data
    assert data["mode"] in ["production", "development"]
    assert isinstance(data["cuda_available"], bool)
    assert isinstance(data["using_mock_vllm"], bool)


def test_vllm_imports_use_mock_on_macos() -> None:
    """Test that imports use mock vLLM on macOS."""
    from app.platform_detect import IS_MACOS, USE_MOCK_VLLM
    from app import vllm_imports

    if IS_MACOS:
        # On macOS, should use mock
        assert USE_MOCK_VLLM
        # Verify they're from mock_vllm module
        import app.mock_vllm
        assert vllm_imports.AsyncLLMEngine is app.mock_vllm.AsyncLLMEngine


def test_llm_service_uses_correct_engine() -> None:
    """Test that LLMService initializes with correct engine."""
    from app.services.llm import LLMService

    service = LLMService(
        model="test-model",
        gpu_memory_utilization=0.7,
    )

    assert service is not None
    assert service.model_name == "test-model"
    assert service.engine is not None


@pytest.mark.asyncio
async def test_llm_service_generate_with_mock() -> None:
    """Test LLMService works with mock engine."""
    from app.services.llm import LLMService
    from app.models import Message

    service = LLMService(
        model="test-model",
        gpu_memory_utilization=0.7,
    )

    messages = [Message(role="user", content="Hello")]
    text, prompt_tokens, completion_tokens = await service.generate(
        messages=messages,
        max_tokens=100,
    )

    assert isinstance(text, str)
    assert len(text) > 0
    assert prompt_tokens > 0
    assert completion_tokens > 0


@pytest.mark.asyncio
async def test_embedding_service_with_mock() -> None:
    """Test EmbeddingService works with mock engine."""
    from app.services.embedding import EmbeddingService

    service = EmbeddingService(
        model="test-model",
        gpu_memory_utilization=0.2,
    )

    embeddings = await service.embed(["test"])
    assert len(embeddings) == 1
    assert len(embeddings[0]) > 0


def test_mode_selection_logic() -> None:
    """Test mode selection logic."""
    from app.platform_detect import get_mode, should_use_mock_vllm, IS_MACOS

    mode = get_mode()
    assert mode in ["production", "development"]

    use_mock = should_use_mock_vllm()
    assert isinstance(use_mock, bool)

    # On macOS, should use mock
    if IS_MACOS:
        assert use_mock


def test_graceful_degradation() -> None:
    """Test that app works gracefully on non-GPU systems."""
    from app.main import app
    from fastapi.testclient import TestClient

    client = TestClient(app)

    # All endpoints should work without errors
    endpoints = [
        "/health",
        "/system",
        "/v1/models",
        "/metrics",
    ]

    for endpoint in endpoints:
        response = client.get(endpoint)
        assert response.status_code in [200, 405], f"{endpoint} failed with {response.status_code}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
