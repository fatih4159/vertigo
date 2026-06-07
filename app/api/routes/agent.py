"""Agent REST API routes."""
from __future__ import annotations

import asyncio
import os
import subprocess
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.agent.factory import AgentFactory
from app.agent.runner import RunMode
from app.config.settings import settings
from app.core.exceptions import AgentNotFoundError, AgentStateError
from sqlalchemy import select as sa_select
from app.storage.repositories import AgentRepository, IterationRepository, AgentEventRepository
from app.database.models import Agent, ToolCall

router = APIRouter(prefix="/agents", tags=["agents"])

# In-memory registry of running AgentRunner instances
_running_agents: Dict[str, Any] = {}


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class CreateAgentRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    masterprompt: str = Field(..., min_length=10)
    model_name: str = Field(default=settings.OLLAMA_DEFAULT_MODEL)
    project_id: Optional[str] = None
    config: Optional[Dict[str, Any]] = None


class AgentResponse(BaseModel):
    id: str
    name: str
    masterprompt: str
    state: str
    model_name: str
    config_json: Optional[Dict] = None
    project_id: Optional[str] = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class StartAgentRequest(BaseModel):
    mode: RunMode = RunMode.RUN_FOREVER
    n_iterations: Optional[int] = None
    goal: Optional[str] = None


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)


class UpdateAgentRequest(BaseModel):
    name: Optional[str] = None
    masterprompt: Optional[str] = None
    model_name: Optional[str] = None
    repository_url: Optional[str] = None
    repository_branch: Optional[str] = None


class ChatResponse(BaseModel):
    agent_id: str
    message: str
    response: str


def _agent_to_dict(agent: Agent) -> Dict[str, Any]:
    config = agent.config_json or {}
    return {
        "id": agent.id,
        "name": agent.name,
        "masterprompt": agent.masterprompt,
        "state": agent.state,
        "model_name": agent.model_name,
        "config_json": config,
        "project_id": agent.project_id,
        "repository_url": config.get("repository_url"),
        "repository_branch": config.get("repository_branch"),
        "workspace_path": config.get("workspace_path"),
        "workspace_file_count": config.get("file_count"),
        "created_at": agent.created_at.isoformat(),
        "updated_at": agent.updated_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_agent(
    body: CreateAgentRequest,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    repo = AgentRepository(db)
    agent = await repo.create(
        name=body.name,
        masterprompt=body.masterprompt,
        model_name=body.model_name,
        config_json=body.config or {},
        project_id=body.project_id,
    )
    await db.commit()
    return _agent_to_dict(agent)


@router.get("")
async def list_agents(
    state: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    repo = AgentRepository(db)
    agents = await repo.list(state=state, limit=limit, offset=offset)
    return [_agent_to_dict(a) for a in agents]


@router.get("/{agent_id}")
async def get_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    repo = AgentRepository(db)
    try:
        agent = await repo.get_or_raise(agent_id)
    except AgentNotFoundError:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    result = _agent_to_dict(agent)
    # Augment with live runner state if running
    if agent_id in _running_agents:
        runner = _running_agents[agent_id]
        result["live_status"] = runner.get_status()
    return result


@router.patch("/{agent_id}")
async def update_agent(
    agent_id: str,
    body: UpdateAgentRequest,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    repo = AgentRepository(db)
    try:
        agent = await repo.get_or_raise(agent_id)
    except AgentNotFoundError:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")

    updates: Dict[str, Any] = {}
    if body.name is not None:
        updates["name"] = body.name
    if body.masterprompt is not None:
        updates["masterprompt"] = body.masterprompt
    if body.model_name is not None:
        updates["model_name"] = body.model_name

    # Repo fields live inside config_json
    if body.repository_url is not None or body.repository_branch is not None:
        config = dict(agent.config_json or {})
        if body.repository_url is not None:
            config["repository_url"] = body.repository_url
        if body.repository_branch is not None:
            config["repository_branch"] = body.repository_branch
        # Clear stale workspace data when repo changes
        if body.repository_url is not None:
            config.pop("workspace_path", None)
            config.pop("file_count", None)
            config.pop("file_tree", None)
        updates["config_json"] = config

    if updates:
        await repo.update(agent_id, **updates)
        await db.commit()

    agent = await repo.get_or_raise(agent_id)
    return _agent_to_dict(agent)


@router.post("/{agent_id}/repository/setup")
async def setup_repository(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    repo = AgentRepository(db)
    try:
        agent = await repo.get_or_raise(agent_id)
    except AgentNotFoundError:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")

    config = dict(agent.config_json or {})
    repository_url = config.get("repository_url")
    if not repository_url:
        raise HTTPException(status_code=400, detail="No repository URL configured for this agent")

    workspace = f"/tmp/aaos/workspaces/{agent_id}"
    branch = config.get("repository_branch") or ""

    os.makedirs(workspace, exist_ok=True)

    if os.path.exists(os.path.join(workspace, ".git")):
        result = subprocess.run(
            ["git", "-C", workspace, "pull"],
            capture_output=True, text=True, timeout=120,
        )
        action = "pulled"
    else:
        cmd = ["git", "clone", "--depth", "1"]
        if branch:
            cmd += ["--branch", branch]
        cmd += [repository_url, workspace]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if result.returncode != 0 and branch:
            # Retry without explicit branch (uses remote default)
            result = subprocess.run(
                ["git", "clone", "--depth", "1", repository_url, workspace],
                capture_output=True, text=True, timeout=180,
            )
        action = "cloned"

    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=f"Git error: {result.stderr[:500]}")

    # Index: collect file tree (skip hidden dirs)
    file_tree: List[str] = []
    for root, dirs, files in os.walk(workspace):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        rel = os.path.relpath(root, workspace)
        for f in files:
            file_tree.append(os.path.join(rel, f) if rel != "." else f)
            if len(file_tree) >= 500:
                break
        if len(file_tree) >= 500:
            break

    config["workspace_path"] = workspace
    config["file_count"] = len(file_tree)
    config["file_tree"] = file_tree[:200]
    await repo.update(agent_id, config_json=config)
    await db.commit()

    return {"status": action, "workspace_path": workspace, "file_count": len(file_tree)}


@router.post("/{agent_id}/start")
async def start_agent(
    agent_id: str,
    body: StartAgentRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    repo = AgentRepository(db)
    try:
        agent = await repo.get_or_raise(agent_id)
    except AgentNotFoundError:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")

    if agent_id in _running_agents:
        runner = _running_agents[agent_id]
        if runner.current_state.value == "RUNNING":
            raise HTTPException(status_code=409, detail="Agent is already running")

    runner = await AgentFactory.create(
        agent_id=agent_id,
        masterprompt=agent.masterprompt,
        model=agent.model_name,
        db_session=db,
        extra_config=agent.config_json or {},
    )
    _running_agents[agent_id] = runner

    async def run_task() -> None:
        try:
            await runner.run(mode=body.mode, n_iterations=body.n_iterations, goal=body.goal)
        finally:
            _running_agents.pop(agent_id, None)
            # Update DB state
            from app.database.session import AsyncSessionLocal
            async with AsyncSessionLocal() as session:
                r = AgentRepository(session)
                await r.update_state(agent_id, "STOPPED")
                await session.commit()

    background_tasks.add_task(run_task)
    await repo.update_state(agent_id, "RUNNING")
    await db.commit()

    return {"agent_id": agent_id, "status": "started", "mode": body.mode}


@router.post("/{agent_id}/pause")
async def pause_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    if agent_id not in _running_agents:
        raise HTTPException(status_code=404, detail="Agent is not running")
    runner = _running_agents[agent_id]
    ok = await runner.pause()
    if not ok:
        raise HTTPException(status_code=409, detail="Cannot pause agent in current state")
    repo = AgentRepository(db)
    await repo.update_state(agent_id, "PAUSED")
    await db.commit()
    return {"agent_id": agent_id, "status": "paused"}


@router.post("/{agent_id}/resume")
async def resume_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    if agent_id not in _running_agents:
        raise HTTPException(status_code=404, detail="Agent is not running")
    runner = _running_agents[agent_id]
    ok = await runner.resume()
    if not ok:
        raise HTTPException(status_code=409, detail="Cannot resume agent in current state")
    repo = AgentRepository(db)
    await repo.update_state(agent_id, "RUNNING")
    await db.commit()
    return {"agent_id": agent_id, "status": "running"}


@router.post("/{agent_id}/stop")
async def stop_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    if agent_id not in _running_agents:
        raise HTTPException(status_code=404, detail="Agent is not running")
    runner = _running_agents[agent_id]
    await runner.stop()
    _running_agents.pop(agent_id, None)
    repo = AgentRepository(db)
    await repo.update_state(agent_id, "STOPPED")
    await db.commit()
    return {"agent_id": agent_id, "status": "stopped"}


@router.post("/{agent_id}/chat")
async def chat_with_agent(
    agent_id: str,
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    repo = AgentRepository(db)
    try:
        agent = await repo.get_or_raise(agent_id)
    except AgentNotFoundError:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")

    if agent_id in _running_agents:
        runner = _running_agents[agent_id]
        response = await runner.user_chat(body.message)
    else:
        # Agent not running - still answer using Ollama directly
        from app.integrations.ollama.client import OllamaClient
        ollama = OllamaClient(
            base_url=settings.OLLAMA_BASE_URL,
            timeout=settings.OLLAMA_TIMEOUT,
            connect_timeout=settings.OLLAMA_CONNECT_TIMEOUT,
            max_retries=settings.OLLAMA_MAX_RETRIES,
            keep_alive=settings.OLLAMA_KEEP_ALIVE,
        )
        messages = [
            {"role": "system", "content": f"You are {agent.name}. {agent.masterprompt}"},
            {"role": "user", "content": body.message},
        ]
        try:
            response = await ollama.chat_with_retry(model=agent.model_name, messages=messages)
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f"Ollama error: {exc}")
        finally:
            await ollama.close()

    return ChatResponse(agent_id=agent_id, message=body.message, response=response)


@router.get("/{agent_id}/iterations")
async def list_iterations(
    agent_id: str,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    repo = AgentRepository(db)
    try:
        await repo.get_or_raise(agent_id)
    except AgentNotFoundError:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")

    iter_repo = IterationRepository(db)
    iterations = await iter_repo.list_for_agent(agent_id, limit=limit, offset=offset)

    # Batch-load tool_calls for all iterations in a single query
    tc_by_iter: Dict[str, List[ToolCall]] = {it.id: [] for it in iterations}
    if iterations:
        tc_stmt = (
            sa_select(ToolCall)
            .where(ToolCall.iteration_id.in_([it.id for it in iterations]))
            .order_by(ToolCall.called_at.asc())
        )
        tc_result = await db.execute(tc_stmt)
        for tc in tc_result.scalars().all():
            tc_by_iter[tc.iteration_id].append(tc)

    return [
        {
            "id": it.id,
            "number": it.number,
            "goal": it.goal,
            "status": it.status,
            "tokens_used": it.tokens_used,
            "started_at": it.started_at.isoformat(),
            "finished_at": it.finished_at.isoformat() if it.finished_at else None,
            "plan_json": it.plan_json,
            "result_json": it.result_json,
            "tool_calls": [
                {
                    "id": tc.id,
                    "tool_name": tc.tool_name,
                    "input_json": tc.input_json,
                    "output_json": tc.output_json,
                    "success": tc.success,
                    "error_message": tc.error_message,
                    "duration_ms": tc.duration_ms,
                    "called_at": tc.called_at.isoformat(),
                }
                for tc in tc_by_iter[it.id]
            ],
        }
        for it in iterations
    ]


@router.get("/{agent_id}/events")
async def list_events(
    agent_id: str,
    event_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    repo = AgentRepository(db)
    try:
        await repo.get_or_raise(agent_id)
    except AgentNotFoundError:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")

    ev_repo = AgentEventRepository(db)
    events = await ev_repo.list_for_agent(agent_id, event_type=event_type, limit=limit, offset=offset)
    return [
        {
            "id": ev.id,
            "event_type": ev.event_type,
            "data": ev.data_json,
            "timestamp": ev.timestamp.isoformat(),
        }
        for ev in events
    ]


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    if agent_id in _running_agents:
        runner = _running_agents[agent_id]
        await runner.stop()
        _running_agents.pop(agent_id, None)
    repo = AgentRepository(db)
    deleted = await repo.delete(agent_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    await db.commit()
