from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import (
    String, Text, Boolean, Integer, Float,
    DateTime, ForeignKey, Index, JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.utcnow()


# ---------------------------------------------------------------------------
# Project
# ---------------------------------------------------------------------------

class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    root_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now, nullable=False)

    agents: Mapped[List["Agent"]] = relationship("Agent", back_populates="project", lazy="select")

    __table_args__ = (Index("ix_projects_name", "name"),)

    def __repr__(self) -> str:
        return f"<Project id={self.id} name={self.name}>"


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    masterprompt: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str] = mapped_column(String(50), nullable=False, default="IDLE")
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    config_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    project_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now, nullable=False)

    project: Mapped[Optional["Project"]] = relationship("Project", back_populates="agents")
    iterations: Mapped[List["Iteration"]] = relationship(
        "Iteration", back_populates="agent", cascade="all, delete-orphan", lazy="select"
    )
    memory_entries: Mapped[List["MemoryEntry"]] = relationship(
        "MemoryEntry", back_populates="agent", cascade="all, delete-orphan", lazy="select"
    )
    events: Mapped[List["AgentEvent"]] = relationship(
        "AgentEvent", back_populates="agent", cascade="all, delete-orphan", lazy="select"
    )
    git_actions: Mapped[List["GitAction"]] = relationship(
        "GitAction", back_populates="agent", cascade="all, delete-orphan", lazy="select"
    )

    __table_args__ = (
        Index("ix_agents_state", "state"),
        Index("ix_agents_project_id", "project_id"),
    )

    def __repr__(self) -> str:
        return f"<Agent id={self.id} name={self.name} state={self.state}>"


# ---------------------------------------------------------------------------
# Iteration
# ---------------------------------------------------------------------------

class Iteration(Base):
    __tablename__ = "iterations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    agent_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False
    )
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    goal: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    plan_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    result_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    started_at: Mapped[datetime] = mapped_column(DateTime, default=_now, nullable=False)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    agent: Mapped["Agent"] = relationship("Agent", back_populates="iterations")
    tool_calls: Mapped[List["ToolCall"]] = relationship(
        "ToolCall", back_populates="iteration", cascade="all, delete-orphan", lazy="select"
    )

    __table_args__ = (
        Index("ix_iterations_agent_id", "agent_id"),
        Index("ix_iterations_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<Iteration id={self.id} agent_id={self.agent_id} number={self.number}>"


# ---------------------------------------------------------------------------
# ToolCall
# ---------------------------------------------------------------------------

class ToolCall(Base):
    __tablename__ = "tool_calls"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    iteration_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("iterations.id", ondelete="CASCADE"), nullable=False
    )
    tool_name: Mapped[str] = mapped_column(String(255), nullable=False)
    input_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    output_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    called_at: Mapped[datetime] = mapped_column(DateTime, default=_now, nullable=False)

    iteration: Mapped["Iteration"] = relationship("Iteration", back_populates="tool_calls")

    __table_args__ = (Index("ix_tool_calls_iteration_id", "iteration_id"),)

    def __repr__(self) -> str:
        return f"<ToolCall id={self.id} tool_name={self.tool_name} success={self.success}>"


# ---------------------------------------------------------------------------
# MemoryEntry
# ---------------------------------------------------------------------------

class MemoryEntry(Base):
    __tablename__ = "memory_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    agent_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False
    )
    memory_type: Mapped[str] = mapped_column(String(20), nullable=False)  # short / mid / long
    key: Mapped[str] = mapped_column(String(512), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    embedding_json: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, nullable=False)
    accessed_at: Mapped[datetime] = mapped_column(DateTime, default=_now, nullable=False)
    access_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    agent: Mapped["Agent"] = relationship("Agent", back_populates="memory_entries")

    __table_args__ = (
        Index("ix_memory_agent_type", "agent_id", "memory_type"),
        Index("ix_memory_key", "key"),
    )

    def __repr__(self) -> str:
        return f"<MemoryEntry id={self.id} type={self.memory_type} key={self.key}>"


# ---------------------------------------------------------------------------
# AgentEvent
# ---------------------------------------------------------------------------

class AgentEvent(Base):
    __tablename__ = "agent_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    agent_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    data_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=_now, nullable=False)

    agent: Mapped["Agent"] = relationship("Agent", back_populates="events")

    __table_args__ = (
        Index("ix_agent_events_agent_id", "agent_id"),
        Index("ix_agent_events_type", "event_type"),
    )

    def __repr__(self) -> str:
        return f"<AgentEvent id={self.id} type={self.event_type}>"


# ---------------------------------------------------------------------------
# GitAction
# ---------------------------------------------------------------------------

class GitAction(Base):
    __tablename__ = "git_actions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    agent_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False
    )
    action_type: Mapped[str] = mapped_column(String(100), nullable=False)  # commit, push, branch, etc.
    repository: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    details_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    requires_confirmation: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    executed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    agent: Mapped["Agent"] = relationship("Agent", back_populates="git_actions")

    __table_args__ = (Index("ix_git_actions_agent_id", "agent_id"),)

    def __repr__(self) -> str:
        return f"<GitAction id={self.id} type={self.action_type}>"


# ---------------------------------------------------------------------------
# GeneratedTool
# ---------------------------------------------------------------------------

class GeneratedTool(Base):
    __tablename__ = "generated_tools"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    version: Mapped[str] = mapped_column(String(50), nullable=False, default="1.0.0")
    description: Mapped[str] = mapped_column(Text, nullable=False)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    input_schema_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    output_schema_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    is_validated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, nullable=False)

    def __repr__(self) -> str:
        return f"<GeneratedTool id={self.id} name={self.name} validated={self.is_validated}>"


# ---------------------------------------------------------------------------
# GeneratedSkill
# ---------------------------------------------------------------------------

class GeneratedSkill(Base):
    __tablename__ = "generated_skills"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    version: Mapped[str] = mapped_column(String(50), nullable=False, default="1.0.0")
    description: Mapped[str] = mapped_column(Text, nullable=False)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    is_validated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, nullable=False)

    def __repr__(self) -> str:
        return f"<GeneratedSkill id={self.id} name={self.name} validated={self.is_validated}>"
