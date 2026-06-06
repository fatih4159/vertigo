"""Base skill class for higher-level agent capabilities."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from app.tools.base import BaseTool, ToolResult


class SkillResult(BaseModel):
    success: bool
    output: Any = None
    error: Optional[str] = None
    tool_calls_made: int = 0
    metadata: Dict[str, Any] = {}


class BaseSkill(ABC):
    """A skill composes multiple tool calls into a higher-level capability."""

    name: str = "base_skill"
    version: str = "1.0.0"
    description: str = "Base skill (abstract)"
    required_tools: List[str] = []

    def __init__(self, tools: Dict[str, BaseTool]) -> None:
        self._tools = tools

    def _get_tool(self, name: str) -> BaseTool:
        tool = self._tools.get(name)
        if tool is None:
            from app.core.exceptions import ToolNotFoundError
            raise ToolNotFoundError(f"Skill '{self.name}' requires tool '{name}' which is not available")
        return tool

    @abstractmethod
    async def execute(self, **kwargs: Any) -> SkillResult:
        ...

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "required_tools": self.required_tools,
        }
