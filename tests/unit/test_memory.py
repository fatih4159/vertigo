"""Unit tests for memory repository."""
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.storage.repositories import MemoryRepository


@pytest.mark.asyncio
async def test_upsert_creates_entry(db_session: AsyncSession, sample_agent):
    repo = MemoryRepository(db_session)
    entry = await repo.upsert(
        agent_id=sample_agent.id,
        memory_type="short",
        key="test_key",
        content="Hello world",
    )
    await db_session.flush()
    assert entry.id is not None
    assert entry.key == "test_key"
    assert entry.content == "Hello world"
    assert entry.memory_type == "short"


@pytest.mark.asyncio
async def test_upsert_updates_existing(db_session: AsyncSession, sample_agent):
    repo = MemoryRepository(db_session)
    await repo.upsert(
        agent_id=sample_agent.id,
        memory_type="short",
        key="shared_key",
        content="original",
    )
    await db_session.flush()

    updated = await repo.upsert(
        agent_id=sample_agent.id,
        memory_type="short",
        key="shared_key",
        content="updated content",
    )
    await db_session.flush()

    assert updated.content == "updated content"
    assert updated.access_count >= 1


@pytest.mark.asyncio
async def test_list_for_agent(db_session: AsyncSession, sample_agent):
    repo = MemoryRepository(db_session)
    for i in range(5):
        await repo.upsert(
            agent_id=sample_agent.id,
            memory_type="short",
            key=f"key_{i}",
            content=f"content {i}",
        )
    await db_session.flush()

    entries = await repo.list_for_agent(sample_agent.id)
    assert len(entries) == 5


@pytest.mark.asyncio
async def test_list_filter_by_type(db_session: AsyncSession, sample_agent):
    repo = MemoryRepository(db_session)
    await repo.upsert(sample_agent.id, "short", "s1", "short content")
    await repo.upsert(sample_agent.id, "long", "l1", "long content")
    await db_session.flush()

    short_entries = await repo.list_for_agent(sample_agent.id, memory_type="short")
    long_entries = await repo.list_for_agent(sample_agent.id, memory_type="long")

    assert len(short_entries) == 1
    assert len(long_entries) == 1
    assert short_entries[0].key == "s1"
    assert long_entries[0].key == "l1"


@pytest.mark.asyncio
async def test_count_for_agent(db_session: AsyncSession, sample_agent):
    repo = MemoryRepository(db_session)
    await repo.upsert(sample_agent.id, "short", "s1", "x")
    await repo.upsert(sample_agent.id, "short", "s2", "x")
    await repo.upsert(sample_agent.id, "long", "l1", "x")
    await db_session.flush()

    counts = await repo.count_for_agent(sample_agent.id)
    assert counts["short"] == 2
    assert counts["long"] == 1


@pytest.mark.asyncio
async def test_list_respects_limit(db_session: AsyncSession, sample_agent):
    repo = MemoryRepository(db_session)
    for i in range(10):
        await repo.upsert(sample_agent.id, "short", f"k{i}", "x")
    await db_session.flush()

    entries = await repo.list_for_agent(sample_agent.id, limit=5)
    assert len(entries) <= 5


@pytest.mark.asyncio
async def test_empty_agent_returns_empty(db_session: AsyncSession, sample_agent):
    repo = MemoryRepository(db_session)
    entries = await repo.list_for_agent(sample_agent.id)
    assert entries == []
    counts = await repo.count_for_agent(sample_agent.id)
    assert counts == {}
