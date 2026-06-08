import redis.asyncio as aioredis
from typing import Optional
from app.core.config import get_settings
from loguru import logger

settings = get_settings()

_redis_client: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client


async def close_redis() -> None:
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None
        logger.info("Redis connection closed")


async def set_cache(key: str, value: str, expire: int = 300) -> None:
    client = await get_redis()
    await client.setex(key, expire, value)


async def get_cache(key: str) -> Optional[str]:
    client = await get_redis()
    return await client.get(key)


async def delete_cache(key: str) -> None:
    client = await get_redis()
    await client.delete(key)


async def set_discovery_status(status: dict) -> None:
    import json
    client = await get_redis()
    await client.set("discovery:status", json.dumps(status), ex=3600)


async def get_discovery_status() -> Optional[dict]:
    import json
    client = await get_redis()
    data = await client.get("discovery:status")
    if data:
        return json.loads(data)
    return None
