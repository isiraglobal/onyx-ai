"""Unit tests for ONYX model engine and hardware detection."""

import pytest
from onyx.models.detector import detect_hardware
from onyx.models.mock import MockModelAdapter
from onyx.models.registry import ModelRegistry
from onyx.models.benchmark import benchmark_model


@pytest.mark.asyncio
async def test_hardware_detector():
    profile = detect_hardware()
    assert profile.os_name in ["Darwin", "Linux", "Windows"]
    assert profile.cpu_cores > 0
    assert profile.ram_gb > 0
    assert profile.disk_free_gb >= 0
    # On M3 Pro Apple Silicon:
    if profile.os_name == "Darwin" and profile.architecture == "arm64":
        assert profile.apple_silicon is True


@pytest.mark.asyncio
async def test_mock_model_adapter():
    mock = MockModelAdapter(model_name="test-mock")
    loaded = await mock.load()
    assert loaded is True
    assert await mock.health_check() is True

    # Test generation
    resp = await mock.generate(prompt="Hello ONYX")
    assert resp.content != ""
    assert resp.model_name == "test-mock"
    assert resp.tokens_prompt > 0
    assert resp.tokens_completion > 0

    # Test custom registered trigger
    mock.register_response("ping", "pong")
    resp_ping = await mock.generate(prompt="send a ping now")
    assert resp_ping.content == "pong"

    # Test streaming
    chunks = []
    async for chunk in mock.stream_generate(prompt="Streaming test"):
        chunks.append(chunk.delta)
    assert len(chunks) > 0
    assert "".join(chunks).strip() != ""

    # Test embeddings
    embeddings = await mock.embed(["test sentence 1", "test sentence 2"])
    assert len(embeddings) == 2
    assert len(embeddings[0]) == 384


@pytest.mark.asyncio
async def test_model_registry_fallback():
    registry = ModelRegistry()
    adapter = await registry.auto_configure()
    assert adapter is not None
    assert adapter.is_loaded is True

    # Verify fallback order lands on a working adapter
    fallback = await registry.get_or_fallback()
    assert fallback is not None
    assert await fallback.health_check() is True

    # Verify model listing
    models = registry.list_models()
    assert len(models) >= 1
    assert any(m["name"] == "mock" for m in models)


@pytest.mark.asyncio
async def test_benchmark_model():
    mock = MockModelAdapter(model_name="bench-mock")
    result = await benchmark_model(mock, prompt="Test benchmark", max_tokens=50)
    assert result.success is True
    assert result.tokens_per_second > 0
    assert result.ttft_seconds >= 0
    assert result.completion_tokens > 0
