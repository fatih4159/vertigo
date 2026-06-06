"""Memory API routes."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.storage.repositories import AgentRepository, MemoryRepository

router = APIRouter(prefix="/agents/{agent_id}/memory", tags=["memory"])


class MemoryEntryResponse(BaseModel):
    id: str
    memory_type: str
    key: str
    content: str
    metadata_json: Optional[Dict] = None
    access_count: int
    created_at: str
    accessed_at: str


@router.get("")
async def list_memory(
    agent_id: str,
    memory_type: Optional[str] = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    repo = AgentRepository(db)
    try:
        await repo.get_or_raise(agent_id)
    except Exception:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")

    mem_repo = MemoryRepository(db)
    entries = await mem_repo.list_for_agent(agent_id, memory_type=memory_type, limit=limit)
    return [
        {
            "id": e.id,
            "memory_type": e.memory_type,
            "key": e.key,
            "content": e.content[:500],
            "metadata": e.metadata_json,
            "access_count": e.access_count,
            "created_at": e.created_at.isoformat(),
            "accessed_at": e.accessed_at.isoformat(),
        }
        for e in entries
    ]


@router.get("/stats")
async def memory_stats(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    repo = AgentRepository(db)
    try:
        await repo.get_or_raise(agent_id)
    except Exception:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")

    mem_repo = MemoryRepository(db)
    counts = await mem_repo.count_for_agent(agent_id)
    return {"agent_id": agent_id, "counts_by_type": counts}
