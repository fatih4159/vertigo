"""Debug skill - analyse errors and suggest/apply fixes."""
from __future__ import annotations

from typing import Any, Dict, Optional

from app.skills.base import BaseSkill, SkillResult
from app.integrations.ollama.client import OllamaClient
from app.config.settings import settings


class DebugSkill(BaseSkill):
    name = "debug"
    version = "1.0.0"
    description = "Analyse an error traceback and apply a fix to the relevant file."
    required_tools = ["read_file", "replace_code"]

    def __init__(self, tools: Dict, ollama: OllamaClient, model: str = "") -> None:
        super().__init__(tools)
        self.ollama = ollama
        self.model = model or settings.OLLAMA_DEFAULT_MODEL

    async def execute(
        self,
        error_message: str,
        file_path: Optional[str] = None,
        apply_fix: bool = True,
    ) -> SkillResult:
        context = ""
        if file_path:
            read_tool = self._get_tool("read_file")
            read_result = await read_tool.run(path=file_path)
            if read_result.success:
                context = f"\n\nFile contents ({file_path}):\n{read_result.output[:4000]}"

        system = """You are an expert debugger. Analyse the error and provide a fix.
If a file is provided, output a JSON with:
{"analysis": "...", "fixed_code": "...", "old_code": "...", "explanation": "..."}
where old_code is the EXACT snippet to replace and fixed_code is the replacement.
If no file provided, output {"analysis": "...", "suggestion": "..."}"""

        prompt = f"""Error:
{error_message}
{context}

Analyse and provide the fix as JSON:"""

        try:
            import json
            raw = await self.ollama.chat_with_retry(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.1},
                format="json",
            )
            data = json.loads(raw)
        except Exception as exc:
            return SkillResult(success=False, error=f"LLM/parse error: {exc}")

        tool_calls = 1
        if apply_fix and file_path and data.get("old_code") and data.get("fixed_code"):
            replace_tool = self._get_tool("replace_code")
            fix_result = await replace_tool.run(
                path=file_path,
                old_code=data["old_code"],
                new_code=data["fixed_code"],
            )
            tool_calls += 1
            if not fix_result.success:
                return SkillResult(
                    success=False,
                    error=f"Fix application failed: {fix_result.error}",
                    tool_calls_made=tool_calls,
                    metadata={"analysis": data.get("analysis")},
                )

        return SkillResult(
            success=True,
            output=data,
            tool_calls_made=tool_calls,
            metadata={"file": file_path, "fix_applied": apply_fix and bool(data.get("old_code"))},
        )
