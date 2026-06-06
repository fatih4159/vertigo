"""Long-term memory - DB-backed, persistent, never auto-evicted, with optional embeddings."""
from __future__ import annotations

import json
import math
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.database.models import MemoryEntry


class LongTermMemory:
    """
    Long-term memory: important facts, learned skills, project context.
    Never auto-evicted. Supports cosine-similarity search if embeddings are provided.
    """

    MEMORY_TYPE = "long"

    def __init__(self, agent_id: str, session: AsyncSession) -> None:
        self.agent_id = agent_id
        self._session = session

    # ------------------------------------------------------------------
    # Core CRUD
    # ------------------------------------------------------------------

    async def set(
        self,
        key: str,
        value: Any,
        metadata: Optional[Dict[str, Any]] = None,
        embedding: Optional[List[float]] = None,
    ) -> None:
        content = json.dumps(value) if not isinstance(value, str) else value

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
            if embedding:
                existing.embedding_json = embedding
        else:
            entry = MemoryEntry(
                agent_id=self.agent_id,
                memory_type=self.MEMORY_TYPE,
                key=key,
                content=content,
                metadata_json=metadata or {},
                embedding_json=embedding,
            )
            self._session.add(entry)

        await self._session.flush()
        logger.debug(f"[LongTermMemory] Set key='{key}' for agent {self.agent_id}")

    async def get(self, key: str) -> Optional[Any]:
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

    # ------------------------------------------------------------------
    # Bulk / Search
    # ------------------------------------------------------------------

    async def list_keys(self, limit: int = 500) -> List[str]:
        stmt = (
            select(MemoryEntry.key)
            .where(
                MemoryEntry.agent_id == self.agent_id,
                MemoryEntry.memory_type == self.MEMORY_TYPE,
            )
            .order_by(MemoryEntry.access_count.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return [row[0] for row in result.fetchall()]

    async def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Keyword search by LIKE. For semantic search use search_by_embedding()."""
        pattern = f"%{query}%"
        stmt = (
            select(MemoryEntry)
            .where(
                MemoryEntry.agent_id == self.agent_id,
                MemoryEntry.memory_type == self.MEMORY_TYPE,
                (MemoryEntry.key.ilike(pattern) | MemoryEntry.content.ilike(pattern)),
            )
            .order_by(MemoryEntry.access_count.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return self._format_entries(result.scalars().all())

    async def search_by_embedding(
        self, query_embedding: List[float], limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Cosine-similarity ranking against stored embeddings (loaded into RAM)."""
        stmt = select(MemoryEntry).where(
            MemoryEntry.agent_id == self.agent_id,
            MemoryEntry.memory_type == self.MEMORY_TYPE,
            MemoryEntry.embedding_json.isnot(None),
        )
        result = await self._session.execute(stmt)
        entries = result.scalars().all()

        scored: List[Tuple[float, MemoryEntry]] = []
        for entry in entries:
            emb = entry.embedding_json
            if emb and len(emb) == len(query_embedding):
                score = self._cosine_similarity(query_embedding, emb)
                scored.append((score, entry))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = [e for _, e in scored[:limit]]
        return self._format_entries(top)

    async def get_all(self, limit: int = 1000) -> Dict[str, Any]:
        stmt = (
            select(MemoryEntry)
            .where(
                MemoryEntry.agent_id == self.agent_id,
                MemoryEntry.memory_type == self.MEMORY_TYPE,
            )
            .order_by(MemoryEntry.access_count.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        out = {}
        for e in result.scalars().all():
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
        emb_count_stmt = select(func.count()).where(
            MemoryEntry.agent_id == self.agent_id,
            MemoryEntry.memory_type == self.MEMORY_TYPE,
            MemoryEntry.embedding_json.isnot(None),
        )
        emb_count = (await self._session.execute(emb_count_stmt)).scalar_one()
        return {
            "type": "long_term",
            "agent_id": self.agent_id,
            "entries": count,
            "entries_with_embeddings": emb_count,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _format_entries(self, entries: List[MemoryEntry]) -> List[Dict[str, Any]]:
        out = []
        for e in entries:
            try:
                value = json.loads(e.content)
            except Exception:
                value = e.content
            out.append({
                "key": e.key,
                "value": value,
                "metadata": e.metadata_json,
                "access_count": e.access_count,
                "created_at": e.created_at.isoformat(),
            })
        return out

    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)
