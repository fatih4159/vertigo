"""End-to-end API tests using FastAPI TestClient."""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.database.session import get_db


# ---------------------------------------------------------------------------
# Override DB to use in-memory test DB
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def client(db_session):
    """HTTP client wired to test DB."""
    app.dependency_overrides[get_db] = lambda: db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Agent CRUD tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_agent(client: AsyncClient):
    resp = await client.post("/api/v1/agents", json={
        "name": "E2E Agent",
        "masterprompt": "You are a test agent for e2e tests.",
        "model_name": "test-model",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "E2E Agent"
    assert data["state"] == "IDLE"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_agents(client: AsyncClient):
    # Create two agents
    for i in range(2):
        await client.post("/api/v1/agents", json={
            "name": f"Agent {i}",
            "masterprompt": "Test masterprompt for e2e.",
            "model_name": "test-model",
        })

    resp = await client.get("/api/v1/agents")
    assert resp.status_code == 200
    agents = resp.json()
    assert isinstance(agents, list)
    assert len(agents) >= 2


@pytest.mark.asyncio
async def test_get_agent(client: AsyncClient):
    create_resp = await client.post("/api/v1/agents", json={
        "name": "Get Test Agent",
        "masterprompt": "Test masterprompt for e2e.",
        "model_name": "test-model",
    })
    agent_id = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/agents/{agent_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == agent_id


@pytest.mark.asyncio
async def test_get_agent_not_found(client: AsyncClient):
    resp = await client.get("/api/v1/agents/nonexistent-id")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_agent(client: AsyncClient):
    create_resp = await client.post("/api/v1/agents", json={
        "name": "Delete Me",
        "masterprompt": "Test masterprompt for e2e.",
        "model_name": "test-model",
    })
    agent_id = create_resp.json()["id"]

    del_resp = await client.delete(f"/api/v1/agents/{agent_id}")
    assert del_resp.status_code == 204

    get_resp = await client.get(f"/api/v1/agents/{agent_id}")
    assert get_resp.status_code == 404


# ---------------------------------------------------------------------------
# Memory tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_memory_stats_empty(client: AsyncClient):
    create_resp = await client.post("/api/v1/agents", json={
        "name": "Memory Agent",
        "masterprompt": "Test masterprompt for e2e.",
        "model_name": "test-model",
    })
    agent_id = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/agents/{agent_id}/memory/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "counts_by_type" in data


@pytest.mark.asyncio
async def test_memory_list_empty(client: AsyncClient):
    create_resp = await client.post("/api/v1/agents", json={
        "name": "Memory List Agent",
        "masterprompt": "Test masterprompt for e2e.",
        "model_name": "test-model",
    })
    agent_id = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/agents/{agent_id}/memory")
    assert resp.status_code == 200
    assert resp.json() == []


# ---------------------------------------------------------------------------
# Iteration tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_iterations_empty(client: AsyncClient):
    create_resp = await client.post("/api/v1/agents", json={
        "name": "Iter Agent",
        "masterprompt": "Test masterprompt for e2e.",
        "model_name": "test-model",
    })
    agent_id = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/agents/{agent_id}/iterations")
    assert resp.status_code == 200
    assert resp.json() == []


# ---------------------------------------------------------------------------
# Tools API tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_tools(client: AsyncClient):
    resp = await client.get("/api/v1/tools")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("status") in ("ok", "healthy", "running")
