"""Ollama model management API routes."""
from __future__ import annotations

from typing import Any, AsyncGenerator, Dict, List

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.integrations.ollama.client import OllamaClient
from app.config.settings import settings
from app.core.exceptions import OllamaConnectionError

import json

router = APIRouter(prefix="/models", tags=["models"])


def _get_ollama() -> OllamaClient:
    return OllamaClient(
        base_url=settings.OLLAMA_BASE_URL,
        timeout=settings.OLLAMA_TIMEOUT,
        max_retries=settings.OLLAMA_MAX_RETRIES,
    )


class PullModelRequest(BaseModel):
    model: str


class GenerateRequest(BaseModel):
    model: str
    prompt: str
    system: str = ""
    options: Dict[str, Any] = {}


@router.get("")
async def list_models() -> List[Dict[str, Any]]:
    client = _get_ollama()
    try:
        models = await client.list_models()
        return models
    except OllamaConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    finally:
        await client.close()


@router.get("/health")
async def ollama_health() -> Dict[str, Any]:
    client = _get_ollama()
    healthy = await client.health_check()
    await client.close()
    return {
        "healthy": healthy,
        "base_url": settings.OLLAMA_BASE_URL,
        "default_model": settings.OLLAMA_DEFAULT_MODEL,
    }


@router.post("/pull")
async def pull_model(body: PullModelRequest) -> StreamingResponse:
    """Stream pull progress as NDJSON."""
    client = _get_ollama()

    async def stream() -> AsyncGenerator[bytes, None]:
        try:
            async for event in client.pull_model(body.model):
                yield (json.dumps(event) + "\n").encode()
        except OllamaConnectionError as exc:
            yield (json.dumps({"error": str(exc)}) + "\n").encode()
        finally:
            await client.close()

    return StreamingResponse(stream(), media_type="application/x-ndjson")


@router.get("/{model_name}/info")
async def model_info(model_name: str) -> Dict[str, Any]:
    client = _get_ollama()
    try:
        info = await client.model_info(model_name)
        return info
    except OllamaConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    finally:
        await client.close()
