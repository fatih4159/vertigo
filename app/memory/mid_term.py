"""Mid-term memory - DB-backed, per-agent, with keyword search."""
from __future__ import annotations

import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.database.models import MemoryEntry
from app.config.settings import settings


class MidTermMemory:
    """
    DB-backed memory that persists agent context across restarts.
    Entries are stored as key/value with JSON content and keyword search.
    """

    MEMORY_TYPE = "mid"

    def __init__(self, agent_id: str, session: AsyncSession, max_entries: int = 200) -> None:
        self.agent_id = agent_id
        self._session = session
        self.max_entries = max_entries

    # ------------------------------------------------------------------
    # Core CRUD
    # ------------------------------------------------------------------

    async def set(
        self,
        key: str,
        value: Any,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        import json

        content = json.dumps(value) if not isinstance(value, str) else value

        # Upsert
        stmt = select(MemoryEntry).where(
            MemoryEntry.agent_id == self.agent_id,
            MemoryEntry.memory_type == self.MEMORY_TYPE,
            MemoryEntry.key == key,
        )
        result = await self._session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            existing.content = content
            existing.metadata_json = metadata or {}
            existing.accessed_at = datetime.utcnow()
            existing.access_count += 1
        else:
            entry = MemoryEntry(
                agent_id=self.agent_id,
                memory_type=self.MEMORY_TYPE,
                key=key,
                content=content,
                metadata_json=metadata or {},
            )
            self._session.add(entry)

        await self._session.flush()
        await self._enforce_limit()

    async def get(self, key: str) -> Optional[Any]:
        import json

        stmt = select(MemoryEntry).where(
            MemoryEntry.agent_id == self.agent_id,
            MemoryEntry.memory_type == self.MEMORY_TYPE,
            MemoryEntry.key == key,
        )
        result = await self._session.execute(stmt)
        entry = result.scalar_one_or_none()

        if entry is None:
            return None

        entry.accessed_at = datetime.utcnow()
        entry.access_count += 1
        await self._session.flush()

        try:
            return json.loads(entry.content)
        except Exception:
            return entry.content

    async def delete(self, key: str) -> bool:
        stmt = delete(MemoryEntry).where(
            MemoryEntry.agent_id == self.agent_id,
            MemoryEntry.memory_type == self.MEMORY_TYPE,
            MemoryEntry.key == key,
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount > 0

    async def has(self, key: str) -> bool:
        return await self.get(key) is not None

    # ------------------------------------------------------------------
    # Bulk
    # ------------------------------------------------------------------

    async def list_keys(self, limit: int = 200) -> List[str]:
        stmt = (
            select(MemoryEntry.key)
            .where(
                MemoryEntry.agent_id == self.agent_id,
                MemoryEntry.memory_type == self.MEMORY_TYPE,
            )
            .order_by(MemoryEntry.accessed_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [row[0] for row in result.fetchall()]

    async def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Simple keyword search in key and content (SQLite LIKE)."""
        import json

        pattern = f"%{query}%"
        stmt = (
            select(MemoryEntry)
            .where(
                MemoryEntry.agent_id == self.agent_id,
                MemoryEntry.memory_type == self.MEMORY_TYPE,
                (MemoryEntry.key.ilike(pattern) | MemoryEntry.content.ilike(pattern)),
            )
            .order_by(MemoryEntry.accessed_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        entries = result.scalars().all()

        out = []
        for e in entries:
            try:
                value = json.loads(e.content)
            except Exception:
                value = e.content
            out.append({"key": e.key, "value": value, "metadata": e.metadata_json})
        return out

    async def get_all(self, limit: int = 200) -> Dict[str, Any]:
        import json

        stmt = (
            select(MemoryEntry)
            .where(
                MemoryEntry.agent_id == self.agent_id,
                MemoryEntry.memory_type == self.MEMORY_TYPE,
            )
            .order_by(MemoryEntry.accessed_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        entries = result.scalars().all()

        out = {}
        for e in entries:
            try:
                out[e.key] = json.loads(e.content)
            except Exception:
                out[e.key] = e.content
        return out

    async def clear(self) -> int:
        stmt = delete(MemoryEntry).where(
            MemoryEntry.agent_id == self.agent_id,
            MemoryEntry.memory_type == self.MEMORY_TYPE,
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    async def stats(self) -> Dict[str, Any]:
        count_stmt = select(func.count()).where(
            MemoryEntry.agent_id == self.agent_id,
            MemoryEntry.memory_type == self.MEMORY_TYPE,
        )
        count = (await self._session.execute(count_stmt)).scalar_one()
        return {
            "type": "mid_term",
            "agent_id": self.agent_id,
            "entries": count,
            "max_entries": self.max_entries,
        }

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    async def _enforce_limit(self) -> None:
        """Remove oldest entries when over the limit."""
        count_stmt = select(func.count()).where(
            MemoryEntry.agent_id == self.agent_id,
            MemoryEntry.memory_type == self.MEMORY_TYPE,
        )
        count = (await self._session.execute(count_stmt)).scalar_one()
        if count > self.max_entries:
            overflow = count - self.max_entries
            subq = (
                select(MemoryEntry.id)
                .where(
                    MemoryEntry.agent_id == self.agent_id,
                    MemoryEntry.memory_type == self.MEMORY_TYPE,
                )
                .order_by(MemoryEntry.accessed_at.asc())
                .limit(overflow)
            )
            ids = (await self._session.execute(subq)).scalars().all()
            if ids:
                await self._session.execute(
                    delete(MemoryEntry).where(MemoryEntry.id.in_(ids))
                )
                logger.debug(f"[MidTermMemory] Evicted {len(ids)} old entries for agent {self.agent_id}")
