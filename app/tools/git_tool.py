"""Git tool wrapping GitClient for agent use."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.tools.base import BaseTool, ToolPermission, ToolResult
from app.integrations.git.client import GitClient
from app.core.exceptions import GitOperationError, GitConfirmationRequired


class GitStatusTool(BaseTool):
    name = "git_status"
    version = "1.0.0"
    description = "Get the current git status of a repository."
    permissions = [ToolPermission.GIT, ToolPermission.READ]

    async def execute(self, repo_path: str) -> ToolResult:
        try:
            client = GitClient(repo_path)
            status = client.status()
            return ToolResult(success=True, output=status)
        except GitOperationError as exc:
            return ToolResult(success=False, error=str(exc))


class GitAddTool(BaseTool):
    name = "git_add"
    version = "1.0.0"
    description = "Stage files for commit. Pass specific paths or leave empty to stage all."
    permissions = [ToolPermission.GIT, ToolPermission.WRITE]

    async def execute(self, repo_path: str, paths: Optional[List[str]] = None) -> ToolResult:
        try:
            client = GitClient(repo_path)
            result = client.add(paths)
            return ToolResult(success=True, output=result or "Files staged")
        except GitOperationError as exc:
            return ToolResult(success=False, error=str(exc))


class GitCommitTool(BaseTool):
    name = "git_commit"
    version = "1.0.0"
    description = "Commit staged changes with a message."
    permissions = [ToolPermission.GIT, ToolPermission.WRITE]

    async def execute(
        self,
        repo_path: str,
        message: str,
        author_name: str = "AAOS Agent",
        author_email: str = "agent@aaos.local",
        require_confirmation: bool = False,
    ) -> ToolResult:
        try:
            client = GitClient(repo_path)
            result = client.commit(
                message=message,
                author_name=author_name,
                author_email=author_email,
                require_confirmation=require_confirmation,
            )
            return ToolResult(success=True, output=result)
        except GitConfirmationRequired as exc:
            return ToolResult(
                success=False,
                error=f"CONFIRMATION_REQUIRED: {exc.message}",
                metadata={"requires_confirmation": True, "details": exc.details},
            )
        except GitOperationError as exc:
            return ToolResult(success=False, error=str(exc))


class GitLogTool(BaseTool):
    name = "git_log"
    version = "1.0.0"
    description = "Show recent git commit history."
    permissions = [ToolPermission.GIT, ToolPermission.READ]

    async def execute(self, repo_path: str, n: int = 10) -> ToolResult:
        try:
            client = GitClient(repo_path)
            log = client.log(n=n)
            return ToolResult(success=True, output=log, metadata={"count": len(log)})
        except GitOperationError as exc:
            return ToolResult(success=False, error=str(exc))


class GitDiffTool(BaseTool):
    name = "git_diff"
    version = "1.0.0"
    description = "Show git diff (unstaged or staged)."
    permissions = [ToolPermission.GIT, ToolPermission.READ]

    async def execute(self, repo_path: str, staged: bool = False, file_path: Optional[str] = None) -> ToolResult:
        try:
            client = GitClient(repo_path)
            diff = client.diff(staged=staged, file_path=file_path)
            return ToolResult(success=True, output=diff)
        except GitOperationError as exc:
            return ToolResult(success=False, error=str(exc))


class GitCreateBranchTool(BaseTool):
    name = "git_create_branch"
    version = "1.0.0"
    description = "Create a new git branch."
    permissions = [ToolPermission.GIT, ToolPermission.WRITE]

    async def execute(self, repo_path: str, branch_name: str, checkout: bool = True) -> ToolResult:
        try:
            client = GitClient(repo_path)
            result = client.create_branch(branch_name, checkout=checkout)
            return ToolResult(success=True, output=result or f"Branch '{branch_name}' created")
        except GitOperationError as exc:
            return ToolResult(success=False, error=str(exc))


class GitCheckoutTool(BaseTool):
    name = "git_checkout"
    version = "1.0.0"
    description = "Checkout a branch or commit ref."
    permissions = [ToolPermission.GIT, ToolPermission.WRITE]

    async def execute(self, repo_path: str, ref: str) -> ToolResult:
        try:
            client = GitClient(repo_path)
            result = client.checkout(ref)
            return ToolResult(success=True, output=result or f"Checked out {ref}")
        except GitOperationError as exc:
            return ToolResult(success=False, error=str(exc))


class GitInitTool(BaseTool):
    name = "git_init"
    version = "1.0.0"
    description = "Initialise a new git repository."
    permissions = [ToolPermission.GIT, ToolPermission.WRITE]

    async def execute(self, repo_path: str, initial_branch: str = "main") -> ToolResult:
        try:
            client = GitClient(repo_path)
            result = client.init(initial_branch)
            return ToolResult(success=True, output=result or f"Repo initialised at {repo_path}")
        except GitOperationError as exc:
            return ToolResult(success=False, error=str(exc))
