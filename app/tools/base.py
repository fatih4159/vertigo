"""Base tool infrastructure for AAOS."""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, Field
from loguru import logger


class ToolPermission(str, Enum):
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    NETWORK = "network"
    GIT = "git"


class ToolResult(BaseModel):
    success: bool
    output: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def raise_if_failed(self) -> None:
        if not self.success:
            from app.core.exceptions import ToolExecutionError
            raise ToolExecutionError(self.error or "Tool execution failed")


class BaseTool(ABC):
    """Abstract base for all AAOS tools."""

    name: str = "base_tool"
    version: str = "1.0.0"
    description: str = "Base tool (abstract)"
    permissions: List[ToolPermission] = []

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def run(self, **kwargs: Any) -> ToolResult:
        """Execute the tool with timing and error wrapping."""
        start = time.monotonic()
        try:
            await self.validate_input(**kwargs)
            result = await self.execute(**kwargs)
            result.duration_ms = (time.monotonic() - start) * 1000
            logger.debug(
                f"[{self.name}] completed in {result.duration_ms:.1f}ms "
                f"success={result.success}"
            )
            return result
        except Exception as exc:
            duration_ms = (time.monotonic() - start) * 1000
            logger.error(f"[{self.name}] raised {type(exc).__name__}: {exc}")
            return ToolResult(
                success=False,
                error=f"{type(exc).__name__}: {exc}",
                duration_ms=duration_ms,
            )

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        """Override in subclass to implement tool logic."""
        ...

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    async def validate_input(self, **kwargs: Any) -> bool:
        """Override to add input validation. Raise ValueError on invalid input."""
        return True

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def get_schema(self) -> Dict[str, Any]:
        """Return a JSON-schema-like description of inputs for this tool."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "permissions": [p.value for p in self.permissions],
            "parameters": self._parameters_schema(),
        }

    def _parameters_schema(self) -> Dict[str, Any]:
        """Override to describe parameters. Returns empty schema by default."""
        return {"type": "object", "properties": {}, "required": []}

    # ------------------------------------------------------------------
    # Representation
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name} v{self.version}>"


class ToolRegistry:
    """Central registry of all available tools."""

    def __init__(self) -> None:
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool
        logger.debug(f"Tool registered: {tool.name} v{tool.version}")

    def unregister(self, name: str) -> None:
        self._tools.pop(name, None)

    def get(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def get_or_raise(self, name: str) -> BaseTool:
        tool = self.get(name)
        if tool is None:
            from app.core.exceptions import ToolNotFoundError
            raise ToolNotFoundError(f"Tool '{name}' is not registered")
        return tool

    def list_tools(self) -> List[Dict[str, Any]]:
        return [t.get_schema() for t in self._tools.values()]

    def all_names(self) -> List[str]:
        return list(self._tools.keys())

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    def __len__(self) -> int:
        return len(self._tools)


# Singleton registry
tool_registry = ToolRegistry()
