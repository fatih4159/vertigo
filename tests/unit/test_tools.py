"""Unit tests for tool infrastructure."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from typing import Any

from app.tools.base import BaseTool, ToolResult, ToolPermission, tool_registry


# ---------------------------------------------------------------------------
# Test tool implementations
# ---------------------------------------------------------------------------

class EchoTool(BaseTool):
    name = "echo_tool"
    description = "Echoes input back"

    async def execute(self, message: str = "hello", **kwargs: Any) -> ToolResult:
        return ToolResult(success=True, output=message)


class FailingTool(BaseTool):
    name = "failing_tool"
    description = "Always fails"

    async def execute(self, **kwargs: Any) -> ToolResult:
        raise RuntimeError("intentional failure")


class SlowTool(BaseTool):
    name = "slow_tool"
    description = "Takes a while"

    async def execute(self, **kwargs: Any) -> ToolResult:
        import asyncio
        await asyncio.sleep(0.01)
        return ToolResult(success=True, output="done")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tool_run_success():
    tool = EchoTool()
    result = await tool.run(message="test_msg")
    assert result.success is True
    assert result.output == "test_msg"


@pytest.mark.asyncio
async def test_tool_run_default_args():
    tool = EchoTool()
    result = await tool.run()
    assert result.success is True
    assert result.output == "hello"


@pytest.mark.asyncio
async def test_tool_run_records_duration():
    tool = SlowTool()
    result = await tool.run()
    assert result.success is True
    assert result.duration_ms > 0


@pytest.mark.asyncio
async def test_tool_run_exception_wrapped():
    """Exceptions in execute() should be caught and returned as failed ToolResult."""
    tool = FailingTool()
    result = await tool.run()
    assert result.success is False
    assert "intentional failure" in (result.error or "")


@pytest.mark.asyncio
async def test_tool_result_raise_if_failed():
    result = ToolResult(success=False, error="oops")
    from app.core.exceptions import ToolExecutionError
    with pytest.raises(ToolExecutionError):
        result.raise_if_failed()


@pytest.mark.asyncio
async def test_tool_result_raise_if_failed_success():
    result = ToolResult(success=True, output="ok")
    result.raise_if_failed()  # should not raise


def test_tool_registry_has_tools():
    """The global registry should contain at least some tools after import."""
    tools = tool_registry.list_tools()
    assert isinstance(tools, list)


def test_tool_registry_get():
    """Registered tools should be retrievable by name."""
    # Register our echo tool temporarily
    tool_registry.register(EchoTool())
    retrieved = tool_registry.get("echo_tool")
    assert retrieved is not None
    assert retrieved.name == "echo_tool"


def test_tool_registry_get_missing():
    assert tool_registry.get("nonexistent_tool_xyz") is None


def test_tool_schema_has_required_fields():
    tool = EchoTool()
    schema = tool.get_schema()
    assert "name" in schema
    assert "description" in schema


def test_tool_permissions_default_empty():
    tool = EchoTool()
    assert isinstance(tool.permissions, list)
