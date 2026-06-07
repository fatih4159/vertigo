"""Tool discovery and on-demand tool creation."""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.extensions.capability_detector import CapabilityGap
from app.extensions.tool_generator import ToolGenerator
from app.tools.base import BaseTool, ToolPermission, ToolResult


class ToolSearchTool(BaseTool):
    name = "tool_search"
    version = "1.0.0"
    description = (
        "Search available tools by capability keyword. "
        "Always call this before tool_create to check whether a suitable tool already exists."
    )
    permissions = [ToolPermission.READ]

    def __init__(self, tools_registry: Dict[str, BaseTool]) -> None:
        self._registry = tools_registry

    def _parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Capability or keyword to search for "
                        "(e.g. 'http request', 'image resize', 'csv parse')"
                    ),
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results to return",
                    "default": 5,
                },
            },
            "required": ["query"],
        }

    async def execute(self, query: str, limit: int = 5) -> ToolResult:
        words = [w for w in query.lower().split() if len(w) >= 2]
        scored: List[tuple[float, Dict[str, Any]]] = []

        for tool in self._registry.values():
            schema = tool.get_schema()
            haystack = f"{schema['name']} {schema['description']}".lower()
            hits = sum(1 for w in words if w in haystack)
            if hits > 0:
                scored.append((hits / max(len(words), 1), schema))

        scored.sort(key=lambda x: x[0], reverse=True)
        results = [s for _, s in scored[:limit]]

        return ToolResult(
            success=True,
            output=results,
            metadata={
                "query": query,
                "total_available": len(self._registry),
                "matches": len(results),
            },
        )


class ToolCreatorTool(BaseTool):
    name = "tool_create"
    version = "1.0.0"
    description = (
        "Generate and register a brand-new tool using an LLM when no existing tool covers "
        "the need. Call tool_search first to confirm no suitable tool exists."
    )
    permissions = [ToolPermission.WRITE, ToolPermission.EXECUTE]

    def __init__(
        self,
        tools_registry: Dict[str, BaseTool],
        register_callback: Callable[[BaseTool], None],
        generator: ToolGenerator,
        db_session: AsyncSession,
    ) -> None:
        self._registry = tools_registry
        self._register = register_callback
        self._generator = generator
        self._db = db_session

    def _parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Snake_case identifier for the new tool (e.g. 'http_get_tool')",
                },
                "description": {
                    "type": "string",
                    "description": "One-sentence description of what the tool should do",
                },
                "capabilities": {
                    "type": "string",
                    "description": (
                        "Detailed explanation of the required capability, "
                        "expected inputs/outputs, and any relevant context"
                    ),
                },
            },
            "required": ["name", "description"],
        }

    async def execute(
        self,
        name: str,
        description: str,
        capabilities: str = "",
    ) -> ToolResult:
        if name in self._registry:
            return ToolResult(
                success=False,
                error=f"Tool '{name}' already exists — use it instead of creating a duplicate",
                output=self._registry[name].get_schema(),
            )

        gap = CapabilityGap(
            name=name,
            description=description,
            evidence=[capabilities] if capabilities else [description],
            suggested_tool_name=name,
            gap_type="tool",
            priority=0.8,
        )

        logger.info(f"[ToolCreatorTool] Generating tool '{name}': {description}")
        db_record = await self._generator.generate_and_register(gap, self._db)

        if db_record is None:
            return ToolResult(
                success=False,
                error=f"Code generation or sandbox validation failed for tool '{name}'",
            )

        tool_instance = _load_tool_instance(db_record.code)
        if tool_instance is None:
            return ToolResult(
                success=False,
                error=(
                    f"Tool '{name}' was generated and saved to the database "
                    "but could not be loaded into the runtime registry"
                ),
                metadata={"db_id": db_record.id},
            )

        self._register(tool_instance)
        logger.info(f"[ToolCreatorTool] Tool '{tool_instance.name}' is now available")

        return ToolResult(
            success=True,
            output=tool_instance.get_schema(),
            metadata={"db_id": db_record.id, "tool_name": tool_instance.name},
        )


def _load_tool_instance(code: str) -> Optional[BaseTool]:
    """Exec sandbox-validated generated code and return an instantiated BaseTool subclass."""
    import app.tools.base as _base

    namespace: Dict[str, Any] = {
        # Provide the base classes so generated code can reference them without a full import
        "BaseTool": _base.BaseTool,
        "ToolResult": _base.ToolResult,
        "ToolPermission": _base.ToolPermission,
    }

    try:
        exec(compile(code, "<generated_tool>", "exec"), namespace)  # noqa: S102
    except Exception as exc:
        logger.error(f"[_load_tool_instance] exec failed: {exc}")
        return None

    for obj in namespace.values():
        if (
            isinstance(obj, type)
            and issubclass(obj, _base.BaseTool)
            and obj is not _base.BaseTool
        ):
            try:
                return obj()
            except TypeError as exc:
                # Generated tool has a constructor that requires arguments — cannot auto-instantiate
                logger.warning(f"[_load_tool_instance] {obj.__name__} needs constructor args: {exc}")
                return None

    logger.error("[_load_tool_instance] No BaseTool subclass found in generated code")
    return None
