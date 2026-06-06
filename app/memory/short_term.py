"""Short-term in-process memory with LRU eviction."""
from __future__ import annotations

import time
from collections import OrderedDict
from typing import Any, Dict, List, Optional

from loguru import logger


class ShortTermMemory:
    """
    Fast in-process LRU memory.
    All writes stay in RAM only - not persisted to DB (DB persistence is mid/long-term's job).
    """

    def __init__(self, max_entries: int = 50) -> None:
        self.max_entries = max_entries
        self._store: OrderedDict[str, Dict[str, Any]] = OrderedDict()

    # ------------------------------------------------------------------
    # Core CRUD
    # ------------------------------------------------------------------

    async def set(
        self,
        key: str,
        value: Any,
        metadata: Optional[Dict[str, Any]] = None,
        ttl_seconds: Optional[float] = None,
    ) -> None:
        if key in self._store:
            self._store.move_to_end(key)
        self._store[key] = {
            "value": value,
            "metadata": metadata or {},
            "created_at": time.time(),
            "accessed_at": time.time(),
            "access_count": 0,
            "expires_at": time.time() + ttl_seconds if ttl_seconds else None,
        }
        while len(self._store) > self.max_entries:
            evicted_key, _ = self._store.popitem(last=False)
            logger.debug(f"[ShortTermMemory] Evicted: {evicted_key}")

    async def get(self, key: str) -> Optional[Any]:
        entry = self._store.get(key)
        if entry is None:
            return None
        if entry["expires_at"] and time.time() > entry["expires_at"]:
            del self._store[key]
            return None
        entry["accessed_at"] = time.time()
        entry["access_count"] += 1
        self._store.move_to_end(key)
        return entry["value"]

    async def delete(self, key: str) -> bool:
        if key in self._store:
            del self._store[key]
            return True
        return False

    async def has(self, key: str) -> bool:
        return await self.get(key) is not None

    # ------------------------------------------------------------------
    # Bulk
    # ------------------------------------------------------------------

    async def list_keys(self, limit: int = 50) -> List[str]:
        self._evict_expired()
        keys = list(reversed(list(self._store.keys())))
        return keys[:limit]

    async def get_all(self) -> Dict[str, Any]:
        self._evict_expired()
        return {k: v["value"] for k, v in self._store.items()}

    async def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Keyword search across string-representable values."""
        self._evict_expired()
        q = query.lower()
        results = []
        for key, entry in reversed(list(self._store.items())):
            value_str = str(entry["value"]).lower()
            if q in key.lower() or q in value_str:
                results.append({"key": key, "value": entry["value"], "metadata": entry["metadata"]})
            if len(results) >= limit:
                break
        return results

    async def clear(self) -> int:
        count = len(self._store)
        self._store.clear()
        return count

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        self._evict_expired()
        return {
            "type": "short_term",
            "entries": len(self._store),
            "max_entries": self.max_entries,
            "utilisation_pct": round(100 * len(self._store) / self.max_entries, 1),
        }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _evict_expired(self) -> None:
        now = time.time()
        expired = [k for k, v in self._store.items() if v["expires_at"] and now > v["expires_at"]]
        for k in expired:
            del self._store[k]
