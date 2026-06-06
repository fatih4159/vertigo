"""Refactor skill - improve existing code via LLM."""
from __future__ import annotations

from typing import Any, Dict, Optional

from app.skills.base import BaseSkill, SkillResult
from app.integrations.ollama.client import OllamaClient
from app.config.settings import settings


class RefactorSkill(BaseSkill):
    name = "refactor"
    version = "1.0.0"
    description = "Refactor existing code to improve quality, readability, or performance."
    required_tools = ["read_file", "write_file"]

    def __init__(self, tools: Dict, ollama: OllamaClient, model: str = "") -> None:
        super().__init__(tools)
        self.ollama = ollama
        self.model = model or settings.OLLAMA_DEFAULT_MODEL

    async def execute(
        self,
        file_path: str,
        instructions: str = "Improve code quality, readability, and add type hints.",
    ) -> SkillResult:
        read_tool = self._get_tool("read_file")
        read_result = await read_tool.run(path=file_path)
        if not read_result.success:
            return SkillResult(success=False, error=f"Could not read file: {read_result.error}", tool_calls_made=1)

        original = read_result.output
        system = """You are an expert code refactoring assistant.
Refactor the provided code according to the instructions.
Output ONLY the refactored code - no markdown, no explanation."""

        prompt = f"""File: {file_path}

Instructions: {instructions}

Original code:
{original[:8000]}

Refactored code:"""

        try:
            refactored = await self.ollama.generate_with_retry(
                model=self.model,
                prompt=prompt,
                system=system,
                options={"temperature": 0.1, "num_predict": 4096},
            )
            if refactored.startswith("```"):
                lines = refactored.split("\n")
                refactored = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

            write_tool = self._get_tool("write_file")
            write_result = await write_tool.run(path=file_path, content=refactored)
            if not write_result.success:
                return SkillResult(success=False, error=write_result.error, tool_calls_made=2)

            return SkillResult(
                success=True,
                output=refactored,
                tool_calls_made=2,
                metadata={"file": file_path, "original_len": len(original), "new_len": len(refactored)},
            )
        except Exception as exc:
            return SkillResult(success=False, error=str(exc), tool_calls_made=1)
