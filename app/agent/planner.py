"""Goal and plan management for the autonomous agent."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

from app.integrations.ollama.client import OllamaClient
from app.config.settings import settings
from app.core.exceptions import PlanningError


@dataclass
class Step:
    id: int
    description: str
    tool: Optional[str] = None
    tool_args: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"  # pending | running | done | failed | skipped
    result: Optional[str] = None
    error: Optional[str] = None


@dataclass
class Plan:
    goal: str
    steps: List[Step] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    rationale: str = ""
    iteration_number: int = 0

    def next_pending_step(self) -> Optional[Step]:
        for step in self.steps:
            if step.status == "pending":
                return step
        return None

    def is_complete(self) -> bool:
        return all(s.status in ("done", "skipped") for s in self.steps)

    def has_failed(self) -> bool:
        return any(s.status == "failed" for s in self.steps)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal": self.goal,
            "rationale": self.rationale,
            "created_at": self.created_at,
            "iteration_number": self.iteration_number,
            "steps": [
                {
                    "id": s.id,
                    "description": s.description,
                    "tool": s.tool,
                    "tool_args": s.tool_args,
                    "status": s.status,
                    "result": s.result,
                    "error": s.error,
                }
                for s in self.steps
            ],
        }


class Planner:
    """
    Determines the current goal and produces a step-by-step plan
    by prompting the local Ollama model.
    """

    PLAN_SYSTEM_PROMPT = """You are a planning module for an autonomous AI agent operating system.
Given the agent's master prompt, current state context, and conversation history,
you must produce a JSON plan with the following structure:

{
  "goal": "single clear sentence stating what the agent should achieve in this iteration",
  "rationale": "brief explanation of why this goal was chosen",
  "steps": [
    {
      "id": 1,
      "description": "human-readable description of this step",
      "tool": "tool_name or null if no tool needed",
      "tool_args": {"arg1": "value1"}
    }
  ]
}

Available tools: {available_tools}

RULES:
- Produce ONLY valid JSON, no markdown fences, no prose outside the JSON.
- If the goal is already achieved, return an empty steps list.
- Steps should be atomic and achievable in one tool call.
- Maximum 10 steps per plan.
- Be specific and actionable.
"""

    def __init__(
        self,
        ollama_client: OllamaClient,
        model: str,
        available_tools: List[str],
    ) -> None:
        self.ollama = ollama_client
        self.model = model
        self.available_tools = available_tools

    async def create_plan(
        self,
        masterprompt: str,
        context: str,
        iteration_number: int,
        previous_results: Optional[List[Dict[str, Any]]] = None,
    ) -> Plan:
        """Ask the LLM to produce a plan for the current iteration."""
        system = self.PLAN_SYSTEM_PROMPT.format(
            available_tools=", ".join(self.available_tools)
        )

        user_msg = f"""Master Prompt:
{masterprompt}

Current Iteration: {iteration_number}

Context / State:
{context}

Previous iteration results:
{json.dumps(previous_results or [], indent=2)[:2000]}

Produce the JSON plan now."""

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user_msg},
        ]

        try:
            raw = await self.ollama.chat_with_retry(
                model=self.model,
                messages=messages,
                options={"temperature": 0.3, "num_predict": 1024},
                format="json",
            )
        except Exception as exc:
            raise PlanningError(f"LLM call failed during planning: {exc}") from exc

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            import re
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group())
                except json.JSONDecodeError:
                    raise PlanningError(f"Could not parse plan JSON from LLM response: {raw[:500]}")
            else:
                raise PlanningError(f"No JSON found in LLM response: {raw[:500]}")

        goal = data.get("goal", "Continue working on assigned tasks")
        rationale = data.get("rationale", "")
        raw_steps = data.get("steps", [])

        steps = []
        for i, s in enumerate(raw_steps[:10]):
            steps.append(
                Step(
                    id=s.get("id", i + 1),
                    description=s.get("description", f"Step {i + 1}"),
                    tool=s.get("tool"),
                    tool_args=s.get("tool_args", {}),
                )
            )

        plan = Plan(
            goal=goal,
            steps=steps,
            rationale=rationale,
            iteration_number=iteration_number,
        )
        logger.info(
            f"[Planner] Created plan for iteration {iteration_number}: "
            f"goal='{goal[:80]}', steps={len(steps)}"
        )
        return plan

    async def determine_goal(
        self,
        masterprompt: str,
        context: str,
        completed_goals: List[str],
    ) -> str:
        """Determine the single most important goal for next iteration."""
        system = """You are a goal selector for an autonomous AI agent.
Given the master prompt, current context, and completed goals, determine the single
most important next goal. Respond with ONLY a single sentence - the goal statement."""

        user_msg = f"""Master Prompt: {masterprompt}

Context: {context}

Completed Goals:
{chr(10).join(f'- {g}' for g in completed_goals[-10:])}

What is the most important next goal?"""

        messages = [{"role": "system", "content": system}, {"role": "user", "content": user_msg}]
        try:
            goal = await self.ollama.chat_with_retry(
                model=self.model,
                messages=messages,
                options={"temperature": 0.2, "num_predict": 100},
            )
            return goal.strip().strip('"').strip("'")
        except Exception as exc:
            logger.warning(f"[Planner] Goal determination failed: {exc}")
            return "Continue working on the assigned tasks as described in the master prompt"
