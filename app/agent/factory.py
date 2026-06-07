"""Agent factory - constructs fully wired AgentRunner instances."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.runner import AgentRunner, RunMode
from app.config.settings import settings
from app.core.events import event_bus
from app.integrations.ollama.client import OllamaClient
from app.tools.base import BaseTool, tool_registry
from app.tools.filesystem import (
    ReadFileTool, WriteFileTool, AppendFileTool,
    ListDirectoryTool, DeleteFileTool, MakeDirectoryTool, MoveFileTool, FileStatsTool,
)
from app.tools.code_editor import (
    InsertCodeTool, ReplaceCodeTool, DeleteLinesTools,
    ApplyPatchTool, SearchInFileTool,
)
from app.tools.shell_command import ShellCommandTool
from app.tools.git_tool import (
    GitStatusTool, GitAddTool, GitCommitTool, GitLogTool,
    GitDiffTool, GitCreateBranchTool, GitCheckoutTool, GitInitTool,
)
from app.tools.ollama_tool import (
    OllamaGenerateTool, OllamaChatTool, OllamaListModelsTool,
    OllamaHealthTool, OllamaJsonChatTool,
)
from app.tools.search_tool import GrepTool, FindFilesTool
from app.tools.project_analyzer import ProjectAnalyzerTool
from app.tools.test_runner import PytestRunnerTool
from app.tools.documentation import (
    ExtractDocstringsTool, GenerateMarkdownDocTool, ReadDocumentationTool,
)
from app.tools.memory_tool import (
    MemoryReadTool, MemoryWriteTool, MemorySearchTool,
    MemoryDeleteTool, MemoryListTool,
)
from app.tools.tool_discovery import ToolCreatorTool, ToolSearchTool
from app.extensions.tool_generator import ToolGenerator


class MemoryManager:
    """Thin facade over short/mid/long-term memory for tools and the runner."""

    def __init__(self, agent_id: str, session: AsyncSession) -> None:
        from app.memory.short_term import ShortTermMemory
        from app.memory.mid_term import MidTermMemory
        from app.memory.long_term import LongTermMemory

        self.agent_id = agent_id
        self.short = ShortTermMemory(max_entries=settings.SHORT_TERM_MAX_ENTRIES)
        self.mid = MidTermMemory(agent_id=agent_id, session=session, max_entries=settings.MID_TERM_MAX_ENTRIES)
        self.long = LongTermMemory(agent_id=agent_id, session=session)

    async def set(
        self,
        key: str,
        value: Any,
        memory_type: str = "short",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        if memory_type == "short":
            await self.short.set(key, value, metadata=metadata)
        elif memory_type == "mid":
            await self.mid.set(key, value, metadata=metadata)
        elif memory_type == "long":
            await self.long.set(key, value, metadata=metadata)
        else:
            await self.short.set(key, value, metadata=metadata)

    async def get(self, key: str, memory_type: str = "short") -> Optional[Any]:
        if memory_type == "short":
            return await self.short.get(key)
        elif memory_type == "mid":
            return await self.mid.get(key)
        elif memory_type == "long":
            return await self.long.get(key)
        # Search all
        v = await self.short.get(key)
        if v is not None:
            return v
        v = await self.mid.get(key)
        if v is not None:
            return v
        return await self.long.get(key)

    async def delete(self, key: str, memory_type: str = "short") -> bool:
        if memory_type == "short":
            return await self.short.delete(key)
        elif memory_type == "mid":
            return await self.mid.delete(key)
        elif memory_type == "long":
            return await self.long.delete(key)
        return False

    async def search(self, query: str, memory_type: str = "all", limit: int = 10) -> List[Dict[str, Any]]:
        results = []
        if memory_type in ("short", "all"):
            results.extend(await self.short.search(query, limit=limit))
        if memory_type in ("mid", "all"):
            results.extend(await self.mid.search(query, limit=limit))
        if memory_type in ("long", "all"):
            results.extend(await self.long.search(query, limit=limit))
        return results[:limit]

    async def list_keys(self, memory_type: str = "short", limit: int = 50) -> List[str]:
        if memory_type == "short":
            return await self.short.list_keys(limit=limit)
        elif memory_type == "mid":
            return await self.mid.list_keys(limit=limit)
        elif memory_type == "long":
            return await self.long.list_keys(limit=limit)
        s = await self.short.list_keys(limit=limit // 3)
        m = await self.mid.list_keys(limit=limit // 3)
        lo = await self.long.list_keys(limit=limit // 3)
        return (s + m + lo)[:limit]

    async def stats(self) -> Dict[str, Any]:
        mid_stats = await self.mid.stats()
        long_stats = await self.long.stats()
        return {
            "short": self.short.stats(),
            "mid": mid_stats,
            "long": long_stats,
        }


def build_default_tools(memory_manager: MemoryManager) -> List[BaseTool]:
    """Instantiate and return all default tools."""
    tools: List[BaseTool] = [
        # Filesystem
        ReadFileTool(),
        WriteFileTool(),
        AppendFileTool(),
        ListDirectoryTool(),
        DeleteFileTool(),
        MakeDirectoryTool(),
        MoveFileTool(),
        FileStatsTool(),
        # Code editing
        InsertCodeTool(),
        ReplaceCodeTool(),
        DeleteLinesTools(),
        ApplyPatchTool(),
        SearchInFileTool(),
        # Shell
        ShellCommandTool(),
        # Git
        GitStatusTool(),
        GitAddTool(),
        GitCommitTool(),
        GitLogTool(),
        GitDiffTool(),
        GitCreateBranchTool(),
        GitCheckoutTool(),
        GitInitTool(),
        # Ollama
        OllamaGenerateTool(),
        OllamaChatTool(),
        OllamaListModelsTool(),
        OllamaHealthTool(),
        OllamaJsonChatTool(),
        # Search
        GrepTool(),
        FindFilesTool(),
        # Analysis
        ProjectAnalyzerTool(),
        # Testing
        PytestRunnerTool(),
        # Documentation
        ExtractDocstringsTool(),
        GenerateMarkdownDocTool(),
        ReadDocumentationTool(),
        # Memory (need memory_manager instance)
        MemoryReadTool(memory_manager),
        MemoryWriteTool(memory_manager),
        MemorySearchTool(memory_manager),
        MemoryDeleteTool(memory_manager),
        MemoryListTool(memory_manager),
    ]
    return tools


class AgentFactory:
    """Wires up and returns a ready-to-run AgentRunner."""

    @staticmethod
    async def create(
        agent_id: str,
        masterprompt: str,
        model: str,
        db_session: AsyncSession,
        extra_config: Optional[Dict[str, Any]] = None,
    ) -> AgentRunner:
        config = extra_config or {}

        ollama_client = OllamaClient(
            base_url=config.get("ollama_base_url", settings.OLLAMA_BASE_URL),
            timeout=config.get("ollama_timeout", settings.OLLAMA_TIMEOUT),
            connect_timeout=config.get("ollama_connect_timeout", settings.OLLAMA_CONNECT_TIMEOUT),
            max_retries=config.get("ollama_max_retries", settings.OLLAMA_MAX_RETRIES),
            keep_alive=config.get("ollama_keep_alive", settings.OLLAMA_KEEP_ALIVE),
        )

        memory_manager = MemoryManager(agent_id=agent_id, session=db_session)
        tools = build_default_tools(memory_manager)

        runner = AgentRunner(
            agent_id=agent_id,
            masterprompt=masterprompt,
            model=model,
            tools=tools,
            memory_manager=memory_manager,
            ollama_client=ollama_client,
            event_bus=event_bus,
            db_session=db_session,
        )

        # Wire discovery tools after runner construction so they share runner._tools
        generator = ToolGenerator(ollama_client=ollama_client, model=model)
        runner.register_tool(ToolSearchTool(tools_registry=runner._tools))
        runner.register_tool(
            ToolCreatorTool(
                tools_registry=runner._tools,
                register_callback=runner.register_tool,
                generator=generator,
                db_session=db_session,
            )
        )

        logger.info(
            f"[AgentFactory] Created agent {agent_id} with model={model}, "
            f"tools={len(runner._tools)}"
        )
        return runner
