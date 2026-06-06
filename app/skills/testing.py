"""Testing skill - generate and run tests."""
from __future__ import annotations

from typing import Any, Dict, Optional

from app.skills.base import BaseSkill, SkillResult
from app.integrations.ollama.client import OllamaClient
from app.config.settings import settings


class TestingSkill(BaseSkill):
    name = "testing"
    version = "1.0.0"
    description = "Generate pytest tests for a Python module and run them."
    required_tools = ["read_file", "write_file", "pytest_runner"]

    def __init__(self, tools: Dict, ollama: OllamaClient, model: str = "") -> None:
        super().__init__(tools)
        self.ollama = ollama
        self.model = model or settings.OLLAMA_DEFAULT_MODEL

    async def execute(
        self,
        source_path: str,
        test_output_path: Optional[str] = None,
        run_tests: bool = True,
    ) -> SkillResult:
        read_tool = self._get_tool("read_file")
        read_result = await read_tool.run(path=source_path)
        if not read_result.success:
            return SkillResult(success=False, error=read_result.error, tool_calls_made=1)

        source = read_result.output
        if not test_output_path:
            from pathlib import Path
            p = Path(source_path)
            test_output_path = str(p.parent / f"test_{p.name}")

        system = """You are an expert Python test engineer.
Write comprehensive pytest tests with:
- Clear test function names following test_<what>_<condition> pattern
- Arrange/Act/Assert structure
- Edge cases and error conditions
- Mock external dependencies
Output ONLY the test code - no markdown, no explanation."""

        prompt = f"""Source file: {source_path}

Source code:
{source[:6000]}

Write pytest tests for this module. Save to: {test_output_path}"""

        try:
            test_code = await self.ollama.generate_with_retry(
                model=self.model,
                prompt=prompt,
                system=system,
                options={"temperature": 0.2, "num_predict": 3000},
            )
            if test_code.startswith("```"):
                lines = test_code.split("\n")
                test_code = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

            write_tool = self._get_tool("write_file")
            write_result = await write_tool.run(path=test_output_path, content=test_code)
            tool_calls = 2
            if not write_result.success:
                return SkillResult(success=False, error=write_result.error, tool_calls_made=tool_calls)

            result_meta = {"test_file": test_output_path, "source": source_path}

            if run_tests:
                runner = self._get_tool("pytest_runner")
                from pathlib import Path
                run_result = await runner.run(
                    path=str(Path(test_output_path).parent),
                    test_path=test_output_path,
                    timeout=60,
                )
                tool_calls += 1
                result_meta["test_results"] = run_result.metadata

                return SkillResult(
                    success=run_result.success,
                    output={"test_code": test_code, "run_output": run_result.output},
                    error=run_result.error,
                    tool_calls_made=tool_calls,
                    metadata=result_meta,
                )

            return SkillResult(
                success=True,
                output=test_code,
                tool_calls_made=tool_calls,
                metadata=result_meta,
            )
        except Exception as exc:
            return SkillResult(success=False, error=str(exc))
