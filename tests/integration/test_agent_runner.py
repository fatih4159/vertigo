"""Integration tests for AgentRunner (mocked Ollama)."""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Any

from app.agent.runner import AgentRunner, RunMode
from app.core.events import EventBus
from app.core.state_machine import AgentState
from app.integrations.ollama.client import OllamaClient
from app.tools.base import BaseTool, ToolResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

class NopTool(BaseTool):
    name = "nop"
    description = "No-op tool for tests"

    async def execute(self, **kwargs: Any) -> ToolResult:
        return ToolResult(success=True, output="nop")


@pytest_asyncio.fixture
async def mock_ollama():
    client = MagicMock(spec=OllamaClient)
    client.chat_with_retry = AsyncMock(return_value='{"tool": "nop", "args": {}, "reasoning": "test"}')
    client.close = AsyncMock()
    return client


@pytest_asyncio.fixture
async def mock_memory():
    mem = MagicMock()
    mem.get_context = AsyncMock(return_value="")
    mem.store = AsyncMock()
    mem.summarize = AsyncMock(return_value="")
    return mem


@pytest_asyncio.fixture
async def runner(db_session, sample_agent, mock_ollama, mock_memory):
    bus = EventBus()
    r = AgentRunner(
        agent_id=sample_agent.id,
        masterprompt=sample_agent.masterprompt,
        model=sample_agent.model_name,
        tools=[NopTool()],
        memory_manager=mock_memory,
        ollama_client=mock_ollama,
        event_bus=bus,
        db_session=db_session,
    )
    return r


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_runner_initial_state(runner):
    assert runner.state_machine.state == AgentState.IDLE


@pytest.mark.asyncio
async def test_runner_pause_from_idle_fails(runner):
    result = await runner.pause()
    assert result is False


@pytest.mark.asyncio
async def test_runner_stop_from_idle(runner):
    """Stopping from IDLE should not raise."""
    await runner.stop()
    # State should be stopped or idle
    assert runner.state_machine.state in (AgentState.STOPPED, AgentState.IDLE)


@pytest.mark.asyncio
async def test_runner_get_status(runner):
    status = runner.get_status()
    assert "state" in status
    assert status["state"] == AgentState.IDLE.value


@pytest.mark.asyncio
async def test_runner_manual_step_single_iteration(runner, mock_ollama):
    """Running manual step should execute exactly one iteration."""
    # Mock planner to return a simple plan
    with patch.object(runner, "_run_single_iteration", new_callable=AsyncMock) as mock_iter:
        mock_iter.return_value = MagicMock(status="success", tokens_used=100)
        await runner.run(mode=RunMode.MANUAL_STEP)
        assert mock_iter.call_count == 1


@pytest.mark.asyncio
async def test_runner_n_iterations(runner):
    """RUN_N_ITERATIONS mode should stop after n iterations."""
    iteration_count = 0

    async def mock_single_iteration(*args, **kwargs):
        nonlocal iteration_count
        iteration_count += 1
        result = MagicMock()
        result.status = "success"
        result.tokens_used = 50
        result.goal = "test"
        return result

    with patch.object(runner, "_run_single_iteration", side_effect=mock_single_iteration):
        await runner.run(mode=RunMode.RUN_N_ITERATIONS, n_iterations=3)

    assert iteration_count == 3


@pytest.mark.asyncio
async def test_runner_user_chat(runner, mock_ollama):
    mock_ollama.chat_with_retry = AsyncMock(return_value="I am a test agent.")
    response = await runner.user_chat("Hello, agent!")
    assert isinstance(response, str)
    assert len(response) > 0
