"""Shell command execution tool with allowlist and timeout enforcement."""
from __future__ import annotations

import asyncio
import shlex
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from app.tools.base import BaseTool, ToolPermission, ToolResult
from app.config.settings import settings
from app.core.exceptions import WorkspaceSecurityError


def _check_command_allowed(command: str) -> str:
    """Validate that the base command is in the allowlist; returns base command name."""
    parts = shlex.split(command)
    if not parts:
        raise ValueError("Empty command")
    base = Path(parts[0]).name  # strip any path prefix
    if base not in settings.ALLOWED_SHELL_COMMANDS:
        raise WorkspaceSecurityError(
            f"Command '{base}' is not in ALLOWED_SHELL_COMMANDS",
            {"command": base, "allowed": settings.ALLOWED_SHELL_COMMANDS},
        )
    return base


class ShellCommandTool(BaseTool):
    name = "shell_command"
    version = "1.0.0"
    description = (
        "Execute a shell command from the allowlist inside a workspace directory. "
        "Returns stdout, stderr, and exit code."
    )
    permissions = [ToolPermission.EXECUTE]

    async def execute(
        self,
        command: str,
        cwd: Optional[str] = None,
        timeout: int = 60,
        env_vars: Optional[Dict[str, str]] = None,
    ) -> ToolResult:
        try:
            _check_command_allowed(command)
        except (WorkspaceSecurityError, ValueError) as exc:
            return ToolResult(success=False, error=str(exc))

        work_dir = Path(cwd).resolve() if cwd else Path(settings.WORKSPACE_ROOT).resolve()
        # Security: ensure cwd is inside allowed workspace
        allowed = [Path(d).resolve() for d in settings.ALLOWED_DIRECTORIES]
        allowed.append(Path(settings.WORKSPACE_ROOT).resolve())
        if not any(str(work_dir).startswith(str(a)) for a in allowed):
            return ToolResult(
                success=False,
                error=f"cwd '{work_dir}' is outside allowed directories",
            )
        if not work_dir.exists():
            work_dir.mkdir(parents=True, exist_ok=True)

        import os
        env = os.environ.copy()
        if env_vars:
            env.update(env_vars)

        logger.info(f"[shell_command] Executing: {command!r} in {work_dir}")
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(work_dir),
                env=env,
            )
            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(), timeout=float(timeout)
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.communicate()
                return ToolResult(
                    success=False,
                    error=f"Command timed out after {timeout}s: {command}",
                )

            stdout = stdout_bytes.decode("utf-8", errors="replace")
            stderr = stderr_bytes.decode("utf-8", errors="replace")
            success = proc.returncode == 0

            return ToolResult(
                success=success,
                output=stdout,
                error=stderr if not success else None,
                metadata={
                    "exit_code": proc.returncode,
                    "stdout": stdout,
                    "stderr": stderr,
                    "command": command,
                    "cwd": str(work_dir),
                },
            )
        except FileNotFoundError as exc:
            return ToolResult(success=False, error=f"Command not found: {exc}")

    def _parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Shell command to execute"},
                "cwd": {"type": "string", "description": "Working directory (must be inside workspace)"},
                "timeout": {"type": "integer", "default": 60, "description": "Timeout in seconds"},
                "env_vars": {"type": "object", "description": "Additional environment variables"},
            },
            "required": ["command"],
        }
