"""Autonomous agent loop engine."""
from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.core.events import Event, EventBus, EventType
from app.core.exceptions import (
    AgentStateError,
    OllamaConnectionError,
    PlanningError,
    ToolExecutionError,
)
from app.core.state_machine import AgentState, StateMachine
from app.agent.planner import Plan, Planner, Step
from app.integrations.ollama.client import OllamaClient
from app.tools.base import BaseTool, ToolResult, tool_registry
from app.database.models import AgentEvent, Iteration, ToolCall


class RunMode(str, Enum):
    RUN_FOREVER = "run_forever"
    RUN_UNTIL_GOAL = "run_until_goal"
    RUN_N_ITERATIONS = "run_n_iterations"
    MANUAL_STEP = "manual_step"


@dataclass
class IterationResult:
    number: int
    goal: str
    plan: Optional[Plan]
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "pending"  # pending | success | failed | paused | stopped
    error: Optional[str] = None
    tokens_used: int = 0
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    finished_at: Optional[str] = None
    summary: str = ""


class AgentRunner:
    """
    Core autonomous execution loop.
    Runs iterations: context -> memory -> plan -> execute tools -> update memory -> log.
    """

    def __init__(
        self,
        agent_id: str,
        masterprompt: str,
        model: str,
        tools: List[BaseTool],
        memory_manager: Any,
        ollama_client: OllamaClient,
        event_bus: EventBus,
        db_session: AsyncSession,
    ) -> None:
        self.agent_id = agent_id
        self.masterprompt = masterprompt
        self.model = model
        self.memory = memory_manager
        self.ollama = ollama_client
        self.event_bus = event_bus
        self.db = db_session

        # Register passed tools into a local dict for fast lookup
        self._tools: Dict[str, BaseTool] = {t.name: t for t in tools}

        self.state_machine = StateMachine()
        self.planner = Planner(
            ollama_client=ollama_client,
            model=model,
            available_tools=[t.get_schema() for t in tools],
        )

        self._iteration_count = 0
        self._completed_goals: List[str] = []
        self._recent_results: List[Dict[str, Any]] = []
        self._stop_event = asyncio.Event()
        self._pause_event = asyncio.Event()
        self._pause_event.set()  # Not paused initially
        self._user_messages: asyncio.Queue = asyncio.Queue()
        self._current_plan: Optional[Plan] = None

    # ------------------------------------------------------------------
    # Public control interface
    # ------------------------------------------------------------------

    async def run(
        self,
        mode: RunMode = RunMode.RUN_FOREVER,
        n_iterations: Optional[int] = None,
        goal: Optional[str] = None,
    ) -> None:
        """Start the autonomous loop. Call from an asyncio task."""
        if not self.state_machine.transition(AgentState.RUNNING, "run() called"):
            raise AgentStateError(
                f"Cannot start agent from state {self.state_machine.state}",
                {"current_state": self.state_machine.state.value},
            )

        await self._publish(EventType.AGENT_STARTED, {"mode": mode, "model": self.model})
        logger.info(f"[Agent {self.agent_id}] Started in mode={mode}")

        target_iterations = n_iterations or settings.AGENT_MAX_ITERATIONS

        try:
            iteration_index = 0
            while not self._stop_event.is_set():
                # Respect pause
                await self._pause_event.wait()

                if self._stop_event.is_set():
                    break

                if mode == RunMode.RUN_N_ITERATIONS and iteration_index >= target_iterations:
                    logger.info(f"[Agent {self.agent_id}] Completed {target_iterations} iterations")
                    break

                self._iteration_count += 1
                iteration_index += 1

                result = await self._run_iteration(self._iteration_count)

                if result.status == "stopped":
                    break

                if mode == RunMode.RUN_UNTIL_GOAL and goal:
                    if self._goal_achieved(goal, result):
                        logger.info(f"[Agent {self.agent_id}] Goal achieved: {goal}")
                        await self._publish(EventType.GOAL_ACHIEVED, {"goal": goal})
                        break

                # Delay between iterations
                await asyncio.sleep(settings.AGENT_ITERATION_DELAY)

        except asyncio.CancelledError:
            logger.info(f"[Agent {self.agent_id}] Task cancelled")
        except Exception as exc:
            logger.exception(f"[Agent {self.agent_id}] Fatal error: {exc}")
            self.state_machine.transition(AgentState.ERROR, str(exc))
            await self._publish(EventType.ERROR_OCCURRED, {"error": str(exc), "fatal": True})
        finally:
            if not self.state_machine.is_stopped():
                self.state_machine.transition(AgentState.STOPPED, "run loop ended")
            await self._publish(EventType.AGENT_STOPPED, {"iterations_completed": self._iteration_count})
            logger.info(f"[Agent {self.agent_id}] Stopped after {self._iteration_count} iterations")

    async def pause(self) -> bool:
        if not self.state_machine.transition(AgentState.PAUSED, "pause() called"):
            return False
        self._pause_event.clear()
        await self._publish(EventType.AGENT_PAUSED, {})
        logger.info(f"[Agent {self.agent_id}] Paused")
        return True

    async def resume(self) -> bool:
        if not self.state_machine.transition(AgentState.RUNNING, "resume() called"):
            return False
        self._pause_event.set()
        await self._publish(EventType.AGENT_RESUMED, {})
        logger.info(f"[Agent {self.agent_id}] Resumed")
        return True

    async def stop(self) -> None:
        self._stop_event.set()
        self._pause_event.set()  # Unblock if paused
        self.state_machine.transition(AgentState.STOPPED, "stop() called")
        await self._publish(EventType.AGENT_STOPPED, {"requested": True})
        logger.info(f"[Agent {self.agent_id}] Stop requested")

    async def user_chat(self, message: str) -> str:
        """Inject a user message and get an LLM response."""
        await self._user_messages.put(message)
        context = await self._build_context()
        messages = [
            {
                "role": "system",
                "content": (
                    f"You are an autonomous AI agent. Master prompt: {self.masterprompt}\n\n"
                    f"Current state: {self.state_machine.state.value}\n"
                    f"Iterations completed: {self._iteration_count}"
                ),
            },
            {"role": "user", "content": message},
        ]
        try:
            response = await self.ollama.chat_with_retry(
                model=self.model,
                messages=messages,
                options={"temperature": 0.7, "num_predict": 512},
            )
            await self._publish(EventType.USER_INTERVENTION, {"message": message, "response": response[:200]})
            return response
        except OllamaConnectionError as exc:
            return f"Error: could not reach Ollama model: {exc}"

    # ------------------------------------------------------------------
    # Core iteration
    # ------------------------------------------------------------------

    async def _run_iteration(self, iteration_number: int) -> IterationResult:
        start = time.monotonic()
        await self._publish(EventType.ITERATION_STARTED, {"iteration": iteration_number})
        logger.info(f"[Agent {self.agent_id}] === Iteration {iteration_number} ===")

        result = IterationResult(
            number=iteration_number,
            goal="",
            plan=None,
        )

        # 1. Build context from memory
        context = await self._build_context()

        # 2. Create plan
        try:
            plan = await self.planner.create_plan(
                masterprompt=self.masterprompt,
                context=context,
                iteration_number=iteration_number,
                previous_results=self._recent_results[-5:],
            )
            result.goal = plan.goal
            result.plan = plan
            self._current_plan = plan
            await self._publish(EventType.PLAN_CREATED, {"goal": plan.goal, "steps": len(plan.steps)})
        except PlanningError as exc:
            logger.error(f"[Agent {self.agent_id}] Planning failed: {exc}")
            result.status = "failed"
            result.error = str(exc)
            await self._persist_iteration(result)
            return result

        # 3. Execute steps
        tool_call_records: List[Dict[str, Any]] = []
        for step in plan.steps:
            if self._stop_event.is_set():
                result.status = "stopped"
                break
            await self._pause_event.wait()
            if self._stop_event.is_set():
                result.status = "stopped"
                break

            step_result = await self._execute_step(step, iteration_number)
            tool_call_records.append(step_result)
            result.tool_calls.append(step_result)

            if not step_result.get("success") and step.tool:
                logger.warning(
                    f"[Agent {self.agent_id}] Step {step.id} failed: {step_result.get('error')}"
                )

        # 4. Summarise iteration
        result.summary = await self._summarise_iteration(plan, tool_call_records)

        # 5. Update memory
        await self._update_memory(result)

        # 6. Persist to DB
        result.status = "success" if result.status == "pending" else result.status
        result.finished_at = datetime.utcnow().isoformat()
        await self._persist_iteration(result, tool_call_records)

        elapsed = time.monotonic() - start
        logger.info(
            f"[Agent {self.agent_id}] Iteration {iteration_number} done in {elapsed:.2f}s"
        )

        self._completed_goals.append(plan.goal)
        self._recent_results.append({"iteration": iteration_number, "goal": plan.goal, "summary": result.summary})
        if len(self._recent_results) > 20:
            self._recent_results = self._recent_results[-20:]

        await self._publish(
            EventType.ITERATION_FINISHED,
            {
                "iteration": iteration_number,
                "goal": plan.goal,
                "status": result.status,
                "elapsed_s": round(elapsed, 2),
            },
        )
        return result

    async def _execute_step(self, step: Step, iteration_number: int) -> Dict[str, Any]:
        """Execute a single plan step, calling the appropriate tool."""
        record = {
            "step_id": step.id,
            "description": step.description,
            "tool": step.tool,
            "tool_args": step.tool_args,
            "success": False,
            "output": None,
            "error": None,
            "duration_ms": 0.0,
            "called_at": datetime.utcnow().isoformat(),
        }

        if not step.tool:
            # No-tool step (observation, reasoning only)
            step.status = "done"
            record["success"] = True
            record["output"] = step.description
            return record

        tool = self._tools.get(step.tool)
        if tool is None:
            err = f"Tool '{step.tool}' not found"
            step.status = "failed"
            step.error = err
            record["error"] = err
            await self._publish(EventType.TOOL_FINISHED, {"tool": step.tool, "success": False, "error": err})
            return record

        await self._publish(EventType.TOOL_STARTED, {"tool": step.tool, "args": step.tool_args})

        try:
            tool_result: ToolResult = await tool.run(**step.tool_args)
            step.result = str(tool_result.output)[:2000] if tool_result.output else ""
            step.status = "done" if tool_result.success else "failed"
            step.error = tool_result.error

            record["success"] = tool_result.success
            record["output"] = tool_result.output
            record["error"] = tool_result.error
            record["duration_ms"] = tool_result.duration_ms

        except Exception as exc:
            err = f"{type(exc).__name__}: {exc}"
            step.status = "failed"
            step.error = err
            record["error"] = err
            logger.error(f"[Agent {self.agent_id}] Tool '{step.tool}' raised: {exc}")

        await self._publish(
            EventType.TOOL_FINISHED,
            {
                "tool": step.tool,
                "success": record["success"],
                "duration_ms": record["duration_ms"],
                "error": record.get("error"),
            },
        )
        return record

    # ------------------------------------------------------------------
    # Context and memory helpers
    # ------------------------------------------------------------------

    async def _build_context(self) -> str:
        """Build a textual context string from short/mid memory for the planner."""
        lines = [
            f"Agent ID: {self.agent_id}",
            f"Current state: {self.state_machine.state.value}",
            f"Iterations completed: {self._iteration_count}",
            f"Recent goals: {', '.join(self._completed_goals[-5:]) if self._completed_goals else 'none'}",
        ]

        # Try to pull relevant context from memory
        try:
            short_keys = await self.memory.list_keys("short", limit=10)
            if short_keys:
                lines.append(f"Short-term memory keys: {', '.join(short_keys[:10])}")
        except Exception:
            pass

        try:
            mid_keys = await self.memory.list_keys("mid", limit=5)
            if mid_keys:
                lines.append(f"Mid-term memory keys: {', '.join(mid_keys[:5])}")
        except Exception:
            pass

        return "\n".join(lines)

    async def _update_memory(self, result: IterationResult) -> None:
        """Store iteration summary in mid-term memory."""
        try:
            key = f"iteration_{result.number}"
            value = {
                "goal": result.goal,
                "status": result.status,
                "summary": result.summary,
                "timestamp": result.finished_at or datetime.utcnow().isoformat(),
            }
            await self.memory.set(key, value, memory_type="mid")
            await self._publish(EventType.MEMORY_UPDATED, {"key": key, "memory_type": "mid"})
        except Exception as exc:
            logger.warning(f"[Agent {self.agent_id}] Memory update failed: {exc}")

    async def _summarise_iteration(
        self, plan: Plan, tool_calls: List[Dict[str, Any]]
    ) -> str:
        """Ask LLM to produce a one-paragraph summary of what happened."""
        if not tool_calls:
            return f"Iteration {plan.iteration_number}: No tool calls executed."

        calls_str = json.dumps(
            [{"tool": tc["tool"], "success": tc["success"], "error": tc.get("error")} for tc in tool_calls],
            indent=2,
        )
        prompt = (
            f"Goal: {plan.goal}\n\nTool calls executed:\n{calls_str[:1000]}\n\n"
            "Write a single sentence summary of what was accomplished."
        )
        try:
            summary = await self.ollama.generate_with_retry(
                model=self.model,
                prompt=prompt,
                options={"temperature": 0.2, "num_predict": 100},
            )
            return summary.strip()
        except Exception:
            successes = sum(1 for tc in tool_calls if tc["success"])
            return f"Completed {successes}/{len(tool_calls)} tool calls for goal: {plan.goal}"

    def _goal_achieved(self, target_goal: str, result: IterationResult) -> bool:
        """Heuristic check if target goal appears achieved."""
        summary_lower = result.summary.lower()
        goal_lower = target_goal.lower()
        keywords = [w for w in goal_lower.split() if len(w) > 4]
        return result.status == "success" and any(kw in summary_lower for kw in keywords)

    # ------------------------------------------------------------------
    # DB persistence
    # ------------------------------------------------------------------

    async def _persist_iteration(
        self,
        result: IterationResult,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        try:
            iteration_row = Iteration(
                agent_id=self.agent_id,
                number=result.number,
                goal=result.goal,
                plan_json=result.plan.to_dict() if result.plan else None,
                result_json={"summary": result.summary, "error": result.error},
                status=result.status,
                started_at=datetime.fromisoformat(result.started_at),
                finished_at=datetime.fromisoformat(result.finished_at) if result.finished_at else None,
                tokens_used=result.tokens_used,
            )
            self.db.add(iteration_row)
            await self.db.flush()

            for tc in (tool_calls or []):
                tc_row = ToolCall(
                    iteration_id=iteration_row.id,
                    tool_name=tc.get("tool") or "unknown",
                    input_json=tc.get("tool_args"),
                    output_json={"output": str(tc.get("output", ""))[:2000]},
                    success=tc.get("success", False),
                    error_message=tc.get("error"),
                    duration_ms=tc.get("duration_ms", 0.0),
                    called_at=datetime.fromisoformat(tc["called_at"]) if tc.get("called_at") else datetime.utcnow(),
                )
                self.db.add(tc_row)

            await self.db.commit()
        except Exception as exc:
            logger.error(f"[Agent {self.agent_id}] DB persist failed: {exc}")
            await self.db.rollback()

    # ------------------------------------------------------------------
    # Event helpers
    # ------------------------------------------------------------------

    async def _publish(self, event_type: EventType, data: Dict[str, Any]) -> None:
        event = Event(type=event_type, data=data, agent_id=self.agent_id)
        try:
            await self.event_bus.publish(event)
        except Exception as exc:
            logger.warning(f"[Agent {self.agent_id}] Event publish failed: {exc}")

        # Also persist to DB
        try:
            ev_row = AgentEvent(
                agent_id=self.agent_id,
                event_type=event_type.value,
                data_json=data,
            )
            self.db.add(ev_row)
            await self.db.flush()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # State accessors
    # ------------------------------------------------------------------

    @property
    def current_state(self) -> AgentState:
        return self.state_machine.state

    def get_status(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "state": self.state_machine.state.value,
            "iteration_count": self._iteration_count,
            "model": self.model,
            "current_goal": self._current_plan.goal if self._current_plan else None,
            "completed_goals": len(self._completed_goals),
        }
