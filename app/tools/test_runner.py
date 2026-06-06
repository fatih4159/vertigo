"""Test runner tool - execute pytest within the workspace."""
from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.tools.base import BaseTool, ToolPermission, ToolResult
from app.tools.filesystem import _resolve_safe
from app.core.exceptions import WorkspaceSecurityError


class PytestRunnerTool(BaseTool):
    name = "pytest_runner"
    version = "1.0.0"
    description = (
        "Run pytest in a workspace directory and return structured results "
        "(pass/fail counts, failures list, coverage summary if available)."
    )
    permissions = [ToolPermission.EXECUTE, ToolPermission.READ]

    async def execute(
        self,
        path: str = ".",
        test_path: Optional[str] = None,
        extra_args: Optional[List[str]] = None,
        timeout: int = 120,
        coverage: bool = False,
    ) -> ToolResult:
        try:
            safe_path = _resolve_safe(path)
        except WorkspaceSecurityError as exc:
            return ToolResult(success=False, error=str(exc))

        args = ["python", "-m", "pytest", "-v", "--tb=short", "--no-header"]
        if coverage:
            args += ["--cov=.", "--cov-report=term-missing"]
        if extra_args:
            args.extend(extra_args)
        if test_path:
            args.append(test_path)

        try:
            proc = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(safe_path),
            )
            try:
                stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=float(timeout))
            except asyncio.TimeoutError:
                proc.kill()
                await proc.communicate()
                return ToolResult(success=False, error=f"pytest timed out after {timeout}s")

            stdout = stdout_b.decode("utf-8", errors="replace")
            stderr = stderr_b.decode("utf-8", errors="replace")
            output = stdout + ("\n" + stderr if stderr.strip() else "")

            # Parse summary line: "3 passed, 1 failed, 2 errors in 0.42s"
            summary_re = re.search(
                r"(\d+) passed|(\d+) failed|(\d+) error", output
            )
            passed = int(re.search(r"(\d+) passed", output).group(1)) if re.search(r"(\d+) passed", output) else 0
            failed = int(re.search(r"(\d+) failed", output).group(1)) if re.search(r"(\d+) failed", output) else 0
            errors = int(re.search(r"(\d+) error", output).group(1)) if re.search(r"(\d+) error", output) else 0

            # Extract failing test names
            failures = re.findall(r"FAILED (.+?) -", output)

            all_passed = proc.returncode == 0

            return ToolResult(
                success=all_passed,
                output=output,
                error=None if all_passed else f"{failed} tests failed, {errors} errors",
                metadata={
                    "passed": passed,
                    "failed": failed,
                    "errors": errors,
                    "failures": failures,
                    "exit_code": proc.returncode,
                    "directory": str(safe_path),
                },
            )
        except FileNotFoundError:
            return ToolResult(success=False, error="pytest not found. Ensure it is installed in the environment.")
