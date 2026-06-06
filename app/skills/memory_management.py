"""Memory management skill - consolidate and prune memory."""
from __future__ import annotations

from typing import Any, Dict, List

from app.skills.base import BaseSkill, SkillResult
from app.integrations.ollama.client import OllamaClient
from app.config.settings import settings


class MemoryManagementSkill(BaseSkill):
    name = "memory_management"
    version = "1.0.0"
    description = "Consolidate short-term memory into long-term storage and prune stale entries."
    required_tools = ["memory_list", "memory_read", "memory_write", "memory_delete"]

    def __init__(self, tools: Dict, ollama: OllamaClient, model: str = "") -> None:
        super().__init__(tools)
        self.ollama = ollama
        self.model = model or settings.OLLAMA_DEFAULT_MODEL

    async def execute(
        self,
        consolidate: bool = True,
        prune_short_term: bool = True,
    ) -> SkillResult:
        list_tool = self._get_tool("memory_list")
        read_tool = self._get_tool("memory_read")
        write_tool = self._get_tool("memory_write")
        delete_tool = self._get_tool("memory_delete")

        tool_calls = 0
        promoted = []
        pruned = []

        if consolidate:
            list_result = await list_tool.run(memory_type="mid", limit=20)
            tool_calls += 1
            keys = list_result.output or []

            for key in keys[:10]:
                read_result = await read_tool.run(key=key, memory_type="mid")
                tool_calls += 1
                if read_result.success and read_result.output:
                    # Promote important memories to long-term
                    value_str = str(read_result.output)
                    if any(kw in key.lower() for kw in ["plan", "goal", "learned", "summary", "important"]):
                        await write_tool.run(key=key, value=read_result.output, memory_type="long")
                        tool_calls += 1
                        promoted.append(key)

        if prune_short_term:
            list_result = await list_tool.run(memory_type="short", limit=50)
            tool_calls += 1
            keys = list_result.output or []
            if len(keys) > 30:
                for key in keys[30:]:
                    await delete_tool.run(key=key, memory_type="short")
                    tool_calls += 1
                    pruned.append(key)

        return SkillResult(
            success=True,
            output={"promoted_to_long": promoted, "pruned_short": pruned},
            tool_calls_made=tool_calls,
            metadata={"promoted_count": len(promoted), "pruned_count": len(pruned)},
        )
