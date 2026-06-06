"""Ollama HTTP client with async streaming, retry, and model management."""
from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx
from loguru import logger

from app.core.exceptions import OllamaConnectionError, OllamaModelError


class OllamaClient:
    """Async Ollama client supporting streaming generate/chat, model listing, and health checks."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        timeout: int = 120,
        max_retries: int = 3,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self._client: Optional[httpx.AsyncClient] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout, connect=10.0),
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    # ------------------------------------------------------------------
    # Health
    # ------------------------------------------------------------------

    async def health_check(self) -> bool:
        """Return True if Ollama is reachable."""
        try:
            client = await self._get_client()
            resp = await client.get("/api/tags", timeout=5.0)
            return resp.status_code == 200
        except Exception as exc:
            logger.warning(f"Ollama health check failed: {exc}")
            return False

    # ------------------------------------------------------------------
    # Models
    # ------------------------------------------------------------------

    async def list_models(self) -> List[Dict[str, Any]]:
        """Return list of locally available models."""
        try:
            client = await self._get_client()
            resp = await client.get("/api/tags")
            resp.raise_for_status()
            data = resp.json()
            return data.get("models", [])
        except httpx.HTTPError as exc:
            raise OllamaConnectionError(f"Failed to list models: {exc}") from exc

    async def pull_model(self, model: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Pull (download) a model, streaming progress events."""
        client = await self._get_client()
        try:
            async with client.stream(
                "POST",
                "/api/pull",
                json={"name": model, "stream": True},
                timeout=httpx.Timeout(3600.0, connect=10.0),
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line.strip():
                        try:
                            yield json.loads(line)
                        except json.JSONDecodeError:
                            pass
        except httpx.HTTPError as exc:
            raise OllamaModelError(f"Failed to pull model '{model}': {exc}") from exc

    async def model_info(self, model: str) -> Dict[str, Any]:
        """Return metadata for a model."""
        try:
            client = await self._get_client()
            resp = await client.post("/api/show", json={"name": model})
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as exc:
            raise OllamaModelError(f"Failed to get info for '{model}': {exc}") from exc

    async def delete_model(self, model: str) -> bool:
        """Delete a local model. Returns True on success."""
        try:
            client = await self._get_client()
            resp = await client.request("DELETE", "/api/delete", json={"name": model})
            return resp.status_code == 200
        except httpx.HTTPError:
            return False

    # ------------------------------------------------------------------
    # Generate (raw completion)
    # ------------------------------------------------------------------

    async def generate(
        self,
        model: str,
        prompt: str,
        system: str = "",
        stream: bool = True,
        options: Optional[Dict[str, Any]] = None,
        images: Optional[List[str]] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream token chunks from /api/generate.

        Yields text chunks as they arrive. Raises OllamaConnectionError on failure.
        """
        payload: Dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": stream,
            "options": options or {},
        }
        if system:
            payload["system"] = system
        if images:
            payload["images"] = images

        client = await self._get_client()
        try:
            async with client.stream("POST", "/api/generate", json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    token = chunk.get("response", "")
                    if token:
                        yield token
                    if chunk.get("done"):
                        break
        except httpx.HTTPStatusError as exc:
            raise OllamaConnectionError(
                f"Ollama generate error {exc.response.status_code}: {exc.response.text}"
            ) from exc
        except httpx.RequestError as exc:
            raise OllamaConnectionError(f"Ollama request failed: {exc}") from exc

    # ------------------------------------------------------------------
    # Chat
    # ------------------------------------------------------------------

    async def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        stream: bool = True,
        options: Optional[Dict[str, Any]] = None,
        format: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream token chunks from /api/chat.

        messages: list of {"role": "user"|"assistant"|"system", "content": str}
        Yields text chunks. Use ``generate_chat_response`` for a full string.
        """
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "options": options or {},
        }
        if format:
            payload["format"] = format

        client = await self._get_client()
        try:
            async with client.stream("POST", "/api/chat", json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    token = chunk.get("message", {}).get("content", "")
                    if token:
                        yield token
                    if chunk.get("done"):
                        break
        except httpx.HTTPStatusError as exc:
            raise OllamaConnectionError(
                f"Ollama chat error {exc.response.status_code}: {exc.response.text}"
            ) from exc
        except httpx.RequestError as exc:
            raise OllamaConnectionError(f"Ollama chat request failed: {exc}") from exc

    # ------------------------------------------------------------------
    # Convenience: non-streaming with retry
    # ------------------------------------------------------------------

    async def generate_with_retry(
        self,
        model: str,
        prompt: str,
        system: str = "",
        options: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Collect full generate response as a string, with exponential-backoff retry."""
        last_error: Optional[Exception] = None
        for attempt in range(1, self.max_retries + 1):
            try:
                parts: List[str] = []
                async for token in self.generate(
                    model=model,
                    prompt=prompt,
                    system=system,
                    stream=True,
                    options=options,
                ):
                    parts.append(token)
                return "".join(parts)
            except OllamaConnectionError as exc:
                last_error = exc
                wait = 2 ** (attempt - 1)
                logger.warning(
                    f"Ollama generate attempt {attempt}/{self.max_retries} failed, "
                    f"retrying in {wait}s: {exc}"
                )
                await asyncio.sleep(wait)
        raise OllamaConnectionError(
            f"Ollama generate failed after {self.max_retries} attempts"
        ) from last_error

    async def chat_with_retry(
        self,
        model: str,
        messages: List[Dict[str, str]],
        options: Optional[Dict[str, Any]] = None,
        format: Optional[str] = None,
    ) -> str:
        """Collect full chat response as string, with exponential-backoff retry."""
        last_error: Optional[Exception] = None
        for attempt in range(1, self.max_retries + 1):
            try:
                parts: List[str] = []
                async for token in self.chat(
                    model=model,
                    messages=messages,
                    stream=True,
                    options=options,
                    format=format,
                ):
                    parts.append(token)
                return "".join(parts)
            except OllamaConnectionError as exc:
                last_error = exc
                wait = 2 ** (attempt - 1)
                logger.warning(
                    f"Ollama chat attempt {attempt}/{self.max_retries} failed, "
                    f"retrying in {wait}s: {exc}"
                )
                await asyncio.sleep(wait)
        raise OllamaConnectionError(
            f"Ollama chat failed after {self.max_retries} attempts"
        ) from last_error

    # ------------------------------------------------------------------
    # JSON-format chat (structured output)
    # ------------------------------------------------------------------

    async def chat_json(
        self,
        model: str,
        messages: List[Dict[str, str]],
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Request JSON-format response and parse it."""
        raw = await self.chat_with_retry(
            model=model, messages=messages, options=options, format="json"
        )
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise OllamaModelError(
                f"Model returned invalid JSON: {raw[:200]}"
            ) from exc

    # ------------------------------------------------------------------
    # Embeddings
    # ------------------------------------------------------------------

    async def embed(self, model: str, prompt: str) -> List[float]:
        """Generate an embedding vector for the given prompt."""
        client = await self._get_client()
        try:
            resp = await client.post("/api/embeddings", json={"model": model, "prompt": prompt})
            resp.raise_for_status()
            data = resp.json()
            return data.get("embedding", [])
        except httpx.HTTPError as exc:
            raise OllamaConnectionError(f"Embedding request failed: {exc}") from exc
