"""Shared pytest fixtures."""
from __future__ import annotations

import asyncio
import os
import tempfile
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.database.base import Base
from app.database.models import Agent, Iteration, ToolCall, MemoryEntry, AgentEvent


# --------------------------------------------------------------------------
# Create a single DB file for the entire test session (module-level setup)
# --------------------------------------------------------------------------
_TMP_DB_FILE = "/tmp/aaos_pytest_test.db"
_DB_URL = f"sqlite+aiosqlite:///{_TMP_DB_FILE}"

# Create tables synchronously at import time (safe to call multiple times)
_SENTINEL = _TMP_DB_FILE + ".ready"

def _init_db() -> None:
    if os.path.exists(_SENTINEL):
        return  # already initialized in this pytest session

    async def _run() -> None:
        # If file exists, delete it and start fresh
        if os.path.exists(_TMP_DB_FILE):
            os.unlink(_TMP_DB_FILE)
        engine = create_async_engine(_DB_URL, echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()

    asyncio.run(_run())
    # Write sentinel to signal initialization is done
    open(_SENTINEL, "w").close()

# Remove stale sentinel from any previous aborted session
if os.path.exists(_SENTINEL) and not os.path.exists(_TMP_DB_FILE):
    os.unlink(_SENTINEL)

_init_db()


@pytest.fixture(scope="session")
def _db_url() -> str:
    return _DB_URL


@pytest_asyncio.fixture(scope="function")
async def db_session(_db_url: str) -> AsyncGenerator[AsyncSession, None]:
    """Fresh async session per test, with cleanup after."""
    engine = create_async_engine(_db_url, echo=False)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        yield session
        await session.rollback()
        # Truncate all tables for isolation
        for table in reversed(Base.metadata.sorted_tables):
            await session.execute(table.delete())
        await session.commit()
    await engine.dispose()


@pytest_asyncio.fixture
async def sample_agent(db_session: AsyncSession) -> Agent:
    """Create a sample agent for tests."""
    from app.storage.repositories import AgentRepository
    repo = AgentRepository(db_session)
    agent = await repo.create(
        name="TestAgent",
        masterprompt="You are a test agent.",
        model_name="test-model",
        config_json={},
    )
    await db_session.flush()
    return agent


@pytest_asyncio.fixture
async def sample_iterations(db_session: AsyncSession, sample_agent: Agent):
    """Create sample iterations for testing."""
    from app.storage.repositories import IterationRepository
    repo = IterationRepository(db_session)
    iterations = []
    for i in range(5):
        it = await repo.create(
            agent_id=sample_agent.id,
            number=i + 1,
            goal=f"Test goal {i + 1}",
        )
        iterations.append(it)
    await db_session.flush()
    return iterations
