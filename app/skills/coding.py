"""Coding skill - write new code files using Ollama."""
from __future__ import annotations

from typing import Any, Dict, Optional

from loguru import logger

from app.skills.base import BaseSkill, SkillResult
from app.integrations.ollama.client import OllamaClient
from app.config.settings import settings


class CodingSkill(BaseSkill):
    name = "coding"
    version = "1.0.0"
    description = "Generate and write new code to a file using an LLM."
    required_tools = ["write_file", "ollama_generate"]

    def __init__(self, tools: Dict, ollama: OllamaClient, model: str = "") -> None:
        super().__init__(tools)
        self.ollama = ollama
        self.model = model or settings.OLLAMA_DEFAULT_MODEL

    async def execute(
        self,
        task: str,
        output_path: str,
        language: str = "python",
        context: str = "",
    ) -> SkillResult:
        system = f"""You are an expert {language} developer.
Write clean, production-quality code with proper error handling, type hints, and docstrings.
Output ONLY the code - no markdown fences, no explanation."""

        context_section = f"Additional context:\n{context}" if context else ""
        prompt = f"""Task: {task}

Output file: {output_path}
Language: {language}

{context_section}

Write the complete {language} implementation:"""

        try:
            code = await self.ollama.generate_with_retry(
                model=self.model,
                prompt=prompt,
                system=system,
                options={"temperature": 0.2, "num_predict": 2048},
            )
            # Strip any accidental markdown fences
            if code.startswith("```"):
                lines = code.split("\n")
                code = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

            write_tool = self._get_tool("write_file")
            result = await write_tool.run(path=output_path, content=code)

            if result.success:
                logger.info(f"[CodingSkill] Wrote {len(code)} chars to {output_path}")
                return SkillResult(
                    success=True,
                    output=code,
                    tool_calls_made=1,
                    metadata={"path": output_path, "chars": len(code), "language": language},
                )
            return SkillResult(success=False, error=result.error, tool_calls_made=1)

        except Exception as exc:
            return SkillResult(success=False, error=str(exc))
