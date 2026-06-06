"""Tools API routes - list available tools and execute them directly."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.tools.base import tool_registry

router = APIRouter(prefix="/tools", tags=["tools"])


class ExecuteToolRequest(BaseModel):
    tool_name: str
    args: Dict[str, Any] = {}


@router.get("")
async def list_tools() -> List[Dict[str, Any]]:
    return tool_registry.list_tools()


@router.get("/{tool_name}")
async def get_tool_schema(tool_name: str) -> Dict[str, Any]:
    tool = tool_registry.get(tool_name)
    if tool is None:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
    return tool.get_schema()


@router.post("/execute")
async def execute_tool(body: ExecuteToolRequest) -> Dict[str, Any]:
    tool = tool_registry.get(body.tool_name)
    if tool is None:
        raise HTTPException(status_code=404, detail=f"Tool '{body.tool_name}' not found")
    result = await tool.run(**body.args)
    return {
        "tool": body.tool_name,
        "success": result.success,
        "output": result.output,
        "error": result.error,
        "duration_ms": result.duration_ms,
        "metadata": result.metadata,
    }
