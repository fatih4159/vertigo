"""LLM-driven tool generator.

Given a CapabilityGap, uses Ollama to generate a new Python tool that fills
the gap, validates it in the Sandbox, then registers it in the database.
"""
from __future__ import annotations

import textwrap
from typing import Any, Dict, Optional

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.database.models import GeneratedTool
from app.extensions.capability_detector import CapabilityGap
from app.extensions.sandbox import Sandbox, ValidationResult
from app.integrations.ollama.client import OllamaClient
from app.storage.repositories import GeneratedToolRepository


_TOOL_SYSTEM_PROMPT = textwrap.dedent("""
You are an expert Python developer creating tools for an autonomous AI agent.
Tools must follow this exact pattern:

```python
from app.tools.base import BaseTool, ToolResult
from typing import Any

class <ClassName>(BaseTool):
    name = "<tool_name>"
    description = "<one-line description>"
    category = "<category>"

    async def run(self, **kwargs: Any) -> ToolResult:
        # Implementation
        try:
            result = ...
            return ToolResult(success=True, output=str(result))
        except Exception as e:
            return ToolResult(success=False, error=str(e))
```

Rules:
- No shell=True
- No eval/exec
- No raw file writes outside /tmp
- Always return ToolResult
- Handle exceptions gracefully
- Keep it focused and minimal
""").strip()


_TEST_SYSTEM_PROMPT = textwrap.dedent("""
You are writing unit tests for a Python tool class.
Write a unittest.TestCase class that tests the tool's run() method.
Use unittest.mock to mock external dependencies (HTTP, filesystem, etc.).
Return ONLY the test class code, no imports beyond unittest and unittest.mock.
""").strip()


class ToolGenerator:
    """Generates new tool code using an LLM and validates it."""

    def __init__(
        self,
        ollama_client: OllamaClient,
        sandbox: Optional[Sandbox] = None,
        model: Optional[str] = None,
    ) -> None:
        self.ollama = ollama_client
        self.sandbox = sandbox or Sandbox(timeout=15)
        self.model = model or settings.OLLAMA_DEFAULT_MODEL

    async def generate_and_register(
        self,
        gap: CapabilityGap,
        db_session: AsyncSession,
    ) -> Optional[GeneratedTool]:
        """
        Full pipeline: design -> generate -> test -> validate -> register.
        Returns the DB record if successful, None otherwise.
        """
        logger.info(f"Generating tool for gap: {gap.name}")

        # 1. Generate tool code
        code = await self._generate_tool_code(gap)
        if not code:
            logger.error(f"LLM returned no code for gap {gap.name}")
            return None

        # 2. Generate tests
        test_code = await self._generate_test_code(code, gap)

        # 3. Validate in sandbox
        validation = self.sandbox.validate(code, test_code if test_code else None)
        if not validation.is_valid:
            logger.warning(
                f"Generated tool for '{gap.name}' failed validation: {validation.errors}"
            )
            # Attempt one retry with the error context
            code = await self._retry_with_errors(code, validation, gap)
            if code:
                validation = self.sandbox.validate(code)

        if not validation.is_valid:
            logger.error(f"Tool generation for '{gap.name}' failed after retry")
            return None

        # 4. Register in DB
        tool_name = gap.suggested_tool_name or gap.name
        repo = GeneratedToolRepository(db_session)
        existing = await repo.get_by_name(tool_name)

        if existing:
            updated = await repo.update(existing.id, code=code, is_validated=True)
            await db_session.commit()
            logger.info(f"Updated existing tool '{tool_name}'")
            return updated

        record = await repo.create(
            name=tool_name,
            description=gap.description,
            code=code,
            is_validated=True,
        )
        await db_session.commit()
        logger.info(f"Registered new tool '{tool_name}' (id={record.id})")
        return record

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _generate_tool_code(self, gap: CapabilityGap) -> Optional[str]:
        prompt = textwrap.dedent(f"""
            Capability gap detected: {gap.name}
            Description: {gap.description}
            Evidence: {'; '.join(gap.evidence[:3])}
            Suggested tool name: {gap.suggested_tool_name or gap.name}

            Generate a complete Python tool class that addresses this gap.
            Return ONLY the Python code, no markdown, no explanation.
        """).strip()

        messages = [
            {"role": "system", "content": _TOOL_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        try:
            response = await self.ollama.chat_with_retry(model=self.model, messages=messages)
            return self._extract_code(response)
        except Exception as exc:
            logger.error(f"Ollama error generating tool: {exc}")
            return None

    async def _generate_test_code(self, code: str, gap: CapabilityGap) -> Optional[str]:
        prompt = textwrap.dedent(f"""
            Write unit tests for this tool:
            ```python
            {code[:2000]}
            ```
            Return ONLY the test class code.
        """).strip()

        messages = [
            {"role": "system", "content": _TEST_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        try:
            response = await self.ollama.chat_with_retry(model=self.model, messages=messages)
            return self._extract_code(response)
        except Exception:
            return None

    async def _retry_with_errors(
        self, code: str, validation: ValidationResult, gap: CapabilityGap
    ) -> Optional[str]:
        error_summary = "\n".join(validation.errors[:5])
        prompt = textwrap.dedent(f"""
            This tool code has validation errors. Fix them and return corrected code only.

            Errors:
            {error_summary}

            Original code:
            ```python
            {code[:3000]}
            ```
        """).strip()

        messages = [
            {"role": "system", "content": _TOOL_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        try:
            response = await self.ollama.chat_with_retry(model=self.model, messages=messages)
            return self._extract_code(response)
        except Exception:
            return None

    @staticmethod
    def _extract_code(text: str) -> str:
        """Strip markdown code fences if present."""
        import re
        # Try to extract from ```python ... ``` block
        match = re.search(r"```(?:python)?\s*\n(.*?)```", text, re.DOTALL)
        if match:
            return match.group(1).strip()
        # Fallback: return as-is, stripping leading/trailing whitespace
        return text.strip()
