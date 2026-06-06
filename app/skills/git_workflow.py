"""Git workflow skill - stage, commit, and branch management with AI-generated messages."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.skills.base import BaseSkill, SkillResult
from app.integrations.ollama.client import OllamaClient
from app.config.settings import settings


class GitWorkflowSkill(BaseSkill):
    name = "git_workflow"
    version = "1.0.0"
    description = "Stage changes, generate a commit message with AI, and commit."
    required_tools = ["git_status", "git_add", "git_diff", "git_commit"]

    def __init__(self, tools: Dict, ollama: OllamaClient, model: str = "") -> None:
        super().__init__(tools)
        self.ollama = ollama
        self.model = model or settings.OLLAMA_DEFAULT_MODEL

    async def execute(
        self,
        repo_path: str,
        message: Optional[str] = None,
        auto_stage: bool = True,
        require_confirmation: bool = False,
    ) -> SkillResult:
        status_tool = self._get_tool("git_status")
        add_tool = self._get_tool("git_add")
        diff_tool = self._get_tool("git_diff")
        commit_tool = self._get_tool("git_commit")

        tool_calls = 0

        # 1. Status
        status_result = await status_tool.run(repo_path=repo_path)
        tool_calls += 1
        if not status_result.success:
            return SkillResult(success=False, error=status_result.error, tool_calls_made=tool_calls)

        status = status_result.output
        if status.get("clean"):
            return SkillResult(
                success=True,
                output="Nothing to commit - working tree clean",
                tool_calls_made=tool_calls,
            )

        # 2. Stage all
        if auto_stage:
            add_result = await add_tool.run(repo_path=repo_path)
            tool_calls += 1
            if not add_result.success:
                return SkillResult(success=False, error=add_result.error, tool_calls_made=tool_calls)

        # 3. Generate commit message if not provided
        if not message:
            diff_result = await diff_tool.run(repo_path=repo_path, staged=True)
            tool_calls += 1
            diff_text = diff_result.output[:2000] if diff_result.success else ""

            prompt = f"""Git diff (staged changes):
{diff_text}

Write a concise, conventional-commits style git commit message (50 chars max subject line).
Output ONLY the commit message, nothing else."""
            try:
                message = await self.ollama.generate_with_retry(
                    model=self.model,
                    prompt=prompt,
                    options={"temperature": 0.2, "num_predict": 100},
                )
                message = message.strip().split("\n")[0][:72]  # First line, max 72 chars
            except Exception:
                changed = status.get("unstaged", []) + status.get("staged", [])
                message = f"chore: update {', '.join(changed[:3])}"

        # 4. Commit
        commit_result = await commit_tool.run(
            repo_path=repo_path,
            message=message,
            require_confirmation=require_confirmation,
        )
        tool_calls += 1

        if not commit_result.success:
            if "CONFIRMATION_REQUIRED" in (commit_result.error or ""):
                return SkillResult(
                    success=False,
                    error=commit_result.error,
                    tool_calls_made=tool_calls,
                    metadata={"requires_confirmation": True, "message": message},
                )
            return SkillResult(success=False, error=commit_result.error, tool_calls_made=tool_calls)

        return SkillResult(
            success=True,
            output=commit_result.output,
            tool_calls_made=tool_calls,
            metadata={"message": message, "repo": repo_path},
        )
