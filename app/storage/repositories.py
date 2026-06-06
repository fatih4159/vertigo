"""Repository pattern: typed DB access for all models."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import (
    Agent, AgentEvent, GeneratedSkill, GeneratedTool,
    GitAction, Iteration, MemoryEntry, Project, ToolCall,
)


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------

class BaseRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session


# ---------------------------------------------------------------------------
# Project
# ---------------------------------------------------------------------------

class ProjectRepository(BaseRepository):
    async def create(self, name: str, root_path: str, description: str = "") -> Project:
        project = Project(id=str(uuid.uuid4()), name=name, description=description, root_path=root_path)
        self._session.add(project)
        await self._session.flush()
        return project

    async def get(self, project_id: str) -> Optional[Project]:
        return await self._session.get(Project, project_id)

    async def list(self, limit: int = 50, offset: int = 0) -> List[Project]:
        stmt = select(Project).order_by(Project.created_at.desc()).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def delete(self, project_id: str) -> bool:
        stmt = delete(Project).where(Project.id == project_id)
        result = await self._session.execute(stmt)
        return result.rowcount > 0


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class AgentRepository(BaseRepository):
    async def create(
        self,
        name: str,
        masterprompt: str,
        model_name: str,
        config_json: Optional[Dict] = None,
        project_id: Optional[str] = None,
    ) -> Agent:
        agent = Agent(
            id=str(uuid.uuid4()),
            name=name,
            masterprompt=masterprompt,
            model_name=model_name,
            state="IDLE",
            config_json=config_json or {},
            project_id=project_id,
        )
        self._session.add(agent)
        await self._session.flush()
        return agent

    async def get(self, agent_id: str) -> Optional[Agent]:
        return await self._session.get(Agent, agent_id)

    async def get_or_raise(self, agent_id: str) -> Agent:
        agent = await self.get(agent_id)
        if agent is None:
            from app.core.exceptions import AgentNotFoundError
            raise AgentNotFoundError(f"Agent '{agent_id}' not found")
        return agent

    async def list(
        self, state: Optional[str] = None, limit: int = 50, offset: int = 0
    ) -> List[Agent]:
        stmt = select(Agent)
        if state:
            stmt = stmt.where(Agent.state == state)
        stmt = stmt.order_by(Agent.created_at.desc()).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update_state(self, agent_id: str, state: str) -> bool:
        stmt = (
            update(Agent)
            .where(Agent.id == agent_id)
            .values(state=state, updated_at=datetime.utcnow())
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def update(self, agent_id: str, **fields: Any) -> bool:
        fields["updated_at"] = datetime.utcnow()
        stmt = update(Agent).where(Agent.id == agent_id).values(**fields)
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def delete(self, agent_id: str) -> bool:
        stmt = delete(Agent).where(Agent.id == agent_id)
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def count(self) -> int:
        result = await self._session.execute(select(func.count()).select_from(Agent))
        return result.scalar_one()


# ---------------------------------------------------------------------------
# Iteration
# ---------------------------------------------------------------------------

class IterationRepository(BaseRepository):
    async def list_for_agent(
        self, agent_id: str, limit: int = 50, offset: int = 0
    ) -> List[Iteration]:
        stmt = (
            select(Iteration)
            .where(Iteration.agent_id == agent_id)
            .order_by(Iteration.started_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get(self, iteration_id: str) -> Optional[Iteration]:
        return await self._session.get(Iteration, iteration_id)

    async def count_for_agent(self, agent_id: str) -> int:
        stmt = select(func.count()).where(Iteration.agent_id == agent_id)
        return (await self._session.execute(stmt)).scalar_one()

    async def get_latest(self, agent_id: str) -> Optional[Iteration]:
        stmt = (
            select(Iteration)
            .where(Iteration.agent_id == agent_id)
            .order_by(Iteration.started_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# ToolCall
# ---------------------------------------------------------------------------

class ToolCallRepository(BaseRepository):
    async def list_for_iteration(self, iteration_id: str) -> List[ToolCall]:
        stmt = (
            select(ToolCall)
            .where(ToolCall.iteration_id == iteration_id)
            .order_by(ToolCall.called_at.asc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())


# ---------------------------------------------------------------------------
# MemoryEntry
# ---------------------------------------------------------------------------

class MemoryRepository(BaseRepository):
    async def list_for_agent(
        self,
        agent_id: str,
        memory_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[MemoryEntry]:
        stmt = select(MemoryEntry).where(MemoryEntry.agent_id == agent_id)
        if memory_type:
            stmt = stmt.where(MemoryEntry.memory_type == memory_type)
        stmt = stmt.order_by(MemoryEntry.accessed_at.desc()).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count_for_agent(self, agent_id: str) -> Dict[str, int]:
        stmt = (
            select(MemoryEntry.memory_type, func.count())
            .where(MemoryEntry.agent_id == agent_id)
            .group_by(MemoryEntry.memory_type)
        )
        result = await self._session.execute(stmt)
        return {row[0]: row[1] for row in result.fetchall()}


# ---------------------------------------------------------------------------
# AgentEvent
# ---------------------------------------------------------------------------

class AgentEventRepository(BaseRepository):
    async def list_for_agent(
        self,
        agent_id: str,
        event_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AgentEvent]:
        stmt = select(AgentEvent).where(AgentEvent.agent_id == agent_id)
        if event_type:
            stmt = stmt.where(AgentEvent.event_type == event_type)
        stmt = stmt.order_by(AgentEvent.timestamp.desc()).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count_for_agent(self, agent_id: str) -> int:
        stmt = select(func.count()).where(AgentEvent.agent_id == agent_id)
        return (await self._session.execute(stmt)).scalar_one()


# ---------------------------------------------------------------------------
# GitAction
# ---------------------------------------------------------------------------

class GitActionRepository(BaseRepository):
    async def create(
        self,
        agent_id: str,
        action_type: str,
        repository: str,
        details: Dict[str, Any],
        requires_confirmation: bool = True,
    ) -> GitAction:
        action = GitAction(
            id=str(uuid.uuid4()),
            agent_id=agent_id,
            action_type=action_type,
            repository=repository,
            details_json=details,
            requires_confirmation=requires_confirmation,
        )
        self._session.add(action)
        await self._session.flush()
        return action

    async def confirm(self, action_id: str) -> bool:
        stmt = (
            update(GitAction)
            .where(GitAction.id == action_id)
            .values(confirmed=True, executed_at=datetime.utcnow())
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def list_for_agent(self, agent_id: str, limit: int = 50) -> List[GitAction]:
        stmt = (
            select(GitAction)
            .where(GitAction.agent_id == agent_id)
            .order_by(GitAction.executed_at.desc().nullslast())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())


# ---------------------------------------------------------------------------
# GeneratedTool / GeneratedSkill
# ---------------------------------------------------------------------------

class GeneratedToolRepository(BaseRepository):
    async def create(
        self, name: str, description: str, code: str,
        input_schema: Optional[Dict] = None,
        output_schema: Optional[Dict] = None,
    ) -> GeneratedTool:
        tool = GeneratedTool(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            code=code,
            input_schema_json=input_schema,
            output_schema_json=output_schema,
        )
        self._session.add(tool)
        await self._session.flush()
        return tool

    async def list(self, validated_only: bool = False, limit: int = 100) -> List[GeneratedTool]:
        stmt = select(GeneratedTool)
        if validated_only:
            stmt = stmt.where(GeneratedTool.is_validated == True)
        stmt = stmt.order_by(GeneratedTool.created_at.desc()).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get(self, tool_id: str) -> Optional[GeneratedTool]:
        return await self._session.get(GeneratedTool, tool_id)

    async def validate(self, tool_id: str) -> bool:
        stmt = update(GeneratedTool).where(GeneratedTool.id == tool_id).values(is_validated=True)
        result = await self._session.execute(stmt)
        return result.rowcount > 0


class GeneratedSkillRepository(BaseRepository):
    async def create(
        self, name: str, description: str, code: str
    ) -> GeneratedSkill:
        skill = GeneratedSkill(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            code=code,
        )
        self._session.add(skill)
        await self._session.flush()
        return skill

    async def list(self, validated_only: bool = False, limit: int = 100) -> List[GeneratedSkill]:
        stmt = select(GeneratedSkill)
        if validated_only:
            stmt = stmt.where(GeneratedSkill.is_validated == True)
        stmt = stmt.order_by(GeneratedSkill.created_at.desc()).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get(self, skill_id: str) -> Optional[GeneratedSkill]:
        return await self._session.get(GeneratedSkill, skill_id)
