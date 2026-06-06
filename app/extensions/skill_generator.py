"""LLM-driven skill generator.

Similar to ToolGenerator but produces multi-step skill classes that
orchestrate sequences of tool calls to accomplish a complex goal.
"""
from __future__ import annotations

import textwrap
from typing import Optional

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.database.models import GeneratedSkill
from app.extensions.capability_detector import CapabilityGap
from app.extensions.sandbox import Sandbox, ValidationResult
from app.integrations.ollama.client import OllamaClient
from app.storage.repositories import GeneratedSkillRepository


_SKILL_SYSTEM_PROMPT = textwrap.dedent("""
You are an expert Python developer creating skills for an autonomous AI agent.
Skills are reusable, multi-step procedures that orchestrate tools.
A skill must follow this pattern:

```python
from app.skills.base import BaseSkill, SkillResult
from typing import Any, Dict

class <ClassName>(BaseSkill):
    name = "<skill_name>"
    description = "<one-line description>"

    async def execute(self, context: Dict[str, Any]) -> SkillResult:
        \"\"\"Execute the skill steps.\"\"\"
        try:
            # Step 1: ...
            # Step 2: ...
            return SkillResult(
                success=True,
                output="<result summary>",
                artifacts=[],
            )
        except Exception as e:
            return SkillResult(success=False, error=str(e))
```

Rules:
- Skills should be higher-level than tools
- Coordinate multiple tool calls
- Store intermediate results in context
- Always return SkillResult
- Handle all exceptions
""").strip()


class SkillGenerator:
    """Generates new skill code using an LLM and validates it."""

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
        available_tools: Optional[list[str]] = None,
    ) -> Optional[GeneratedSkill]:
        """Full pipeline: generate -> validate -> register."""
        logger.info(f"Generating skill for gap: {gap.name}")

        code = await self._generate_skill_code(gap, available_tools or [])
        if not code:
            logger.error(f"LLM returned no skill code for gap {gap.name}")
            return None

        validation = self.sandbox.validate_syntax_only(code)
        if not validation.is_valid:
            logger.warning(f"Generated skill for '{gap.name}' has syntax errors: {validation.errors}")
            code = await self._retry_with_errors(code, validation)
            if code:
                validation = self.sandbox.validate_syntax_only(code)

        if not validation.is_valid:
            logger.error(f"Skill generation for '{gap.name}' failed after retry")
            return None

        skill_name = gap.suggested_skill_name or gap.name
        repo = GeneratedSkillRepository(db_session)
        existing = await repo.get_by_name(skill_name)

        if existing:
            updated = await repo.update(existing.id, code=code, is_validated=True)
            await db_session.commit()
            return updated

        record = await repo.create(
            name=skill_name,
            description=gap.description,
            code=code,
            is_validated=True,
        )
        await db_session.commit()
        logger.info(f"Registered new skill '{skill_name}' (id={record.id})")
        return record

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _generate_skill_code(
        self, gap: CapabilityGap, available_tools: list[str]
    ) -> Optional[str]:
        tools_str = ", ".join(available_tools) if available_tools else "none specified"
        prompt = textwrap.dedent(f"""
            Skill gap: {gap.name}
            Description: {gap.description}
            Evidence: {'; '.join(gap.evidence[:3])}
            Available tools: {tools_str}
            Suggested skill name: {gap.suggested_skill_name or gap.name}

            Generate a complete Python skill class that fills this gap.
            Return ONLY the Python code, no markdown, no explanation.
        """).strip()

        messages = [
            {"role": "system", "content": _SKILL_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        try:
            response = await self.ollama.chat_with_retry(model=self.model, messages=messages)
            return self._extract_code(response)
        except Exception as exc:
            logger.error(f"Ollama error generating skill: {exc}")
            return None

    async def _retry_with_errors(
        self, code: str, validation: ValidationResult
    ) -> Optional[str]:
        error_summary = "\n".join(validation.errors[:5])
        prompt = textwrap.dedent(f"""
            Fix the following skill code. Errors:
            {error_summary}

            Original code:
            ```python
            {code[:3000]}
            ```
            Return ONLY the fixed Python code.
        """).strip()

        messages = [
            {"role": "system", "content": _SKILL_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        try:
            response = await self.ollama.chat_with_retry(model=self.model, messages=messages)
            return self._extract_code(response)
        except Exception:
            return None

    @staticmethod
    def _extract_code(text: str) -> str:
        import re
        match = re.search(r"```(?:python)?\s*\n(.*?)```", text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return text.strip()
