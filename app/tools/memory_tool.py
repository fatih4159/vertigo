"""Memory read/write tools for agents."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.tools.base import BaseTool, ToolPermission, ToolResult


class MemoryReadTool(BaseTool):
    name = "memory_read"
    version = "1.0.0"
    description = "Read a value from agent memory by key."
    permissions = [ToolPermission.READ]

    def __init__(self, memory_manager: Any) -> None:
        self._memory = memory_manager

    async def execute(self, key: str, memory_type: str = "short") -> ToolResult:
        try:
            value = await self._memory.get(key, memory_type=memory_type)
            if value is None:
                return ToolResult(success=False, error=f"Key '{key}' not found in {memory_type} memory")
            return ToolResult(success=True, output=value, metadata={"key": key, "memory_type": memory_type})
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))


class MemoryWriteTool(BaseTool):
    name = "memory_write"
    version = "1.0.0"
    description = "Write a key-value pair to agent memory."
    permissions = [ToolPermission.WRITE]

    def __init__(self, memory_manager: Any) -> None:
        self._memory = memory_manager

    async def execute(
        self,
        key: str,
        value: Any,
        memory_type: str = "short",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ToolResult:
        try:
            await self._memory.set(key, value, memory_type=memory_type, metadata=metadata)
            return ToolResult(
                success=True,
                output=f"Stored '{key}' in {memory_type} memory",
                metadata={"key": key, "memory_type": memory_type},
            )
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))


class MemorySearchTool(BaseTool):
    name = "memory_search"
    version = "1.0.0"
    description = "Search agent memory by keyword or semantic similarity."
    permissions = [ToolPermission.READ]

    def __init__(self, memory_manager: Any) -> None:
        self._memory = memory_manager

    async def execute(
        self,
        query: str,
        memory_type: str = "all",
        limit: int = 10,
    ) -> ToolResult:
        try:
            results = await self._memory.search(query, memory_type=memory_type, limit=limit)
            return ToolResult(
                success=True,
                output=results,
                metadata={"query": query, "count": len(results)},
            )
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))


class MemoryDeleteTool(BaseTool):
    name = "memory_delete"
    version = "1.0.0"
    description = "Delete a key from agent memory."
    permissions = [ToolPermission.WRITE]

    def __init__(self, memory_manager: Any) -> None:
        self._memory = memory_manager

    async def execute(self, key: str, memory_type: str = "short") -> ToolResult:
        try:
            deleted = await self._memory.delete(key, memory_type=memory_type)
            if deleted:
                return ToolResult(success=True, output=f"Deleted '{key}' from {memory_type} memory")
            return ToolResult(success=False, error=f"Key '{key}' not found in {memory_type} memory")
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))


class MemoryListTool(BaseTool):
    name = "memory_list"
    version = "1.0.0"
    description = "List all keys in agent memory."
    permissions = [ToolPermission.READ]

    def __init__(self, memory_manager: Any) -> None:
        self._memory = memory_manager

    async def execute(self, memory_type: str = "all", limit: int = 50) -> ToolResult:
        try:
            keys = await self._memory.list_keys(memory_type=memory_type, limit=limit)
            return ToolResult(
                success=True,
                output=keys,
                metadata={"count": len(keys), "memory_type": memory_type},
            )
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))
