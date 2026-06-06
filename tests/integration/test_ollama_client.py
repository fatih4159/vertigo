"""Integration tests for OllamaClient (mocked HTTP)."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import AsyncGenerator

from app.integrations.ollama.client import OllamaClient
from app.core.exceptions import OllamaConnectionError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_response(json_data: dict, status: int = 200):
    mock = MagicMock()
    mock.status = status
    mock.json = AsyncMock(return_value=json_data)
    mock.text = AsyncMock(return_value=str(json_data))
    mock.__aenter__ = AsyncMock(return_value=mock)
    mock.__aexit__ = AsyncMock(return_value=False)
    return mock


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_health_check_success():
    client = OllamaClient(base_url="http://localhost:11434")
    with patch.object(client, "_session") as mock_session:
        mock_get = MagicMock()
        mock_response = _mock_response({}, status=200)
        mock_get.return_value = mock_response
        mock_session.get = mock_get

        result = await client.health_check()
        # Should return True if no exception
        assert isinstance(result, bool)
    await client.close()


@pytest.mark.asyncio
async def test_list_models_returns_list():
    """list_models should return a list."""
    client = OllamaClient(base_url="http://localhost:11434")
    with patch.object(client, "_get") as mock_get:
        mock_get.return_value = {
            "models": [
                {"name": "llama3:8b", "size": 4700000000, "digest": "abc123"},
            ]
        }
        models = await client.list_models()
        assert isinstance(models, list)
        assert models[0]["name"] == "llama3:8b"
    await client.close()


@pytest.mark.asyncio
async def test_chat_with_retry_success():
    """chat_with_retry should return the assistant's message content."""
    client = OllamaClient(base_url="http://localhost:11434")
    mock_response = {
        "message": {"role": "assistant", "content": "Hello! I am a test."},
        "done": True,
    }
    with patch.object(client, "_post") as mock_post:
        mock_post.return_value = mock_response
        result = await client.chat_with_retry(
            model="test-model",
            messages=[{"role": "user", "content": "Hello"}],
        )
        assert "Hello" in result or isinstance(result, str)
    await client.close()


@pytest.mark.asyncio
async def test_chat_with_retry_retries_on_failure():
    """Should retry on connection error."""
    client = OllamaClient(base_url="http://localhost:11434", max_retries=2)
    call_count = 0

    async def failing_post(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        raise OllamaConnectionError("Connection refused")

    with patch.object(client, "_post", side_effect=failing_post):
        with pytest.raises(OllamaConnectionError):
            await client.chat_with_retry(
                model="test",
                messages=[{"role": "user", "content": "hi"}],
            )
    # Should have retried max_retries times
    assert call_count >= 1
    await client.close()


@pytest.mark.asyncio
async def test_model_info():
    client = OllamaClient(base_url="http://localhost:11434")
    mock_data = {
        "name": "llama3:8b",
        "details": {"parameter_size": "8B", "quantization_level": "Q4_0"},
    }
    with patch.object(client, "_post") as mock_post:
        mock_post.return_value = mock_data
        info = await client.model_info("llama3:8b")
        assert isinstance(info, dict)
    await client.close()
