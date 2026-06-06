"""Ollama LLM tool - lets the agent invoke sub-LLM calls as a tool."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.tools.base import BaseTool, ToolPermission, ToolResult
from app.integrations.ollama.client import OllamaClient
from app.config.settings import settings
from app.core.exceptions import OllamaConnectionError


def _get_client() -> OllamaClient:
    return OllamaClient(
        base_url=settings.OLLAMA_BASE_URL,
        timeout=settings.OLLAMA_TIMEOUT,
        max_retries=settings.OLLAMA_MAX_RETRIES,
    )


class OllamaGenerateTool(BaseTool):
    name = "ollama_generate"
    version = "1.0.0"
    description = "Generate text using a local Ollama model (raw completion)."
    permissions = [ToolPermission.NETWORK]

    async def execute(
        self,
        prompt: str,
        model: Optional[str] = None,
        system: str = "",
        options: Optional[Dict[str, Any]] = None,
    ) -> ToolResult:
        model = model or settings.OLLAMA_DEFAULT_MODEL
        try:
            client = _get_client()
            response = await client.generate_with_retry(
                model=model, prompt=prompt, system=system, options=options
            )
            await client.close()
            return ToolResult(
                success=True,
                output=response,
                metadata={"model": model, "prompt_len": len(prompt)},
            )
        except OllamaConnectionError as exc:
            return ToolResult(success=False, error=str(exc))


class OllamaChatTool(BaseTool):
    name = "ollama_chat"
    version = "1.0.0"
    description = "Send a chat conversation to a local Ollama model."
    permissions = [ToolPermission.NETWORK]

    async def execute(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> ToolResult:
        model = model or settings.OLLAMA_DEFAULT_MODEL
        try:
            client = _get_client()
            response = await client.chat_with_retry(
                model=model, messages=messages, options=options
            )
            await client.close()
            return ToolResult(
                success=True,
                output=response,
                metadata={"model": model, "message_count": len(messages)},
            )
        except OllamaConnectionError as exc:
            return ToolResult(success=False, error=str(exc))


class OllamaListModelsTool(BaseTool):
    name = "ollama_list_models"
    version = "1.0.0"
    description = "List locally available Ollama models."
    permissions = [ToolPermission.NETWORK]

    async def execute(self) -> ToolResult:
        try:
            client = _get_client()
            models = await client.list_models()
            await client.close()
            return ToolResult(
                success=True,
                output=models,
                metadata={"count": len(models)},
            )
        except OllamaConnectionError as exc:
            return ToolResult(success=False, error=str(exc))


class OllamaHealthTool(BaseTool):
    name = "ollama_health"
    version = "1.0.0"
    description = "Check if the Ollama service is running."
    permissions = [ToolPermission.NETWORK]

    async def execute(self) -> ToolResult:
        client = _get_client()
        healthy = await client.health_check()
        await client.close()
        return ToolResult(
            success=healthy,
            output={"healthy": healthy, "base_url": settings.OLLAMA_BASE_URL},
            error=None if healthy else "Ollama service is not reachable",
        )


class OllamaJsonChatTool(BaseTool):
    name = "ollama_json_chat"
    version = "1.0.0"
    description = (
        "Ask a local Ollama model a question and get a structured JSON response. "
        "Useful for planning, reasoning, and tool selection."
    )
    permissions = [ToolPermission.NETWORK]

    async def execute(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> ToolResult:
        model = model or settings.OLLAMA_DEFAULT_MODEL
        try:
            client = _get_client()
            data = await client.chat_json(model=model, messages=messages, options=options)
            await client.close()
            return ToolResult(success=True, output=data, metadata={"model": model})
        except OllamaConnectionError as exc:
            return ToolResult(success=False, error=str(exc))
