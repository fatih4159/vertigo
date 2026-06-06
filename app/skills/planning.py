"""Planning skill - break a high-level goal into a saved project plan."""
from __future__ import annotations

import json
from typing import Any, Dict, Optional

from app.skills.base import BaseSkill, SkillResult
from app.integrations.ollama.client import OllamaClient
from app.config.settings import settings


class PlanningSkill(BaseSkill):
    name = "planning"
    version = "1.0.0"
    description = "Decompose a complex goal into a saved milestone plan."
    required_tools = ["write_file", "memory_write"]

    def __init__(self, tools: Dict, ollama: OllamaClient, model: str = "") -> None:
        super().__init__(tools)
        self.ollama = ollama
        self.model = model or settings.OLLAMA_DEFAULT_MODEL

    async def execute(
        self,
        goal: str,
        save_path: Optional[str] = None,
        context: str = "",
    ) -> SkillResult:
        system = """You are an expert project planner for software engineering tasks.
Produce a structured JSON plan with milestones and tasks.
Format:
{
  "goal": "...",
  "milestones": [
    {"id": 1, "name": "...", "description": "...", "tasks": ["task1", "task2"]}
  ],
  "estimated_iterations": 10,
  "risks": ["..."]
}"""

        context_section = f"Context:\n{context}" if context else ""
        prompt = f"""Goal: {goal}

{context_section}

Create a detailed milestone plan as JSON:"""

        try:
            raw = await self.ollama.chat_with_retry(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.3, "num_predict": 1500},
                format="json",
            )
            plan_data = json.loads(raw)
        except json.JSONDecodeError:
            plan_data = {"goal": goal, "milestones": [], "raw_plan": raw}
        except Exception as exc:
            return SkillResult(success=False, error=str(exc))

        tool_calls = 1
        if save_path:
            write_tool = self._get_tool("write_file")
            write_result = await write_tool.run(
                path=save_path,
                content=json.dumps(plan_data, indent=2),
            )
            tool_calls += 1
            if not write_result.success:
                return SkillResult(success=False, error=write_result.error, tool_calls_made=tool_calls)

        # Also store in memory
        try:
            mem_tool = self._get_tool("memory_write")
            await mem_tool.run(key="current_plan", value=plan_data, memory_type="long")
            tool_calls += 1
        except Exception:
            pass

        return SkillResult(
            success=True,
            output=plan_data,
            tool_calls_made=tool_calls,
            metadata={"goal": goal, "milestones": len(plan_data.get("milestones", []))},
        )
