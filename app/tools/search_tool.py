"""Search tools - grep across workspace files."""
from __future__ import annotations

import asyncio
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiofiles

from app.tools.base import BaseTool, ToolPermission, ToolResult
from app.tools.filesystem import _resolve_safe
from app.core.exceptions import WorkspaceSecurityError


class GrepTool(BaseTool):
    name = "grep"
    version = "1.0.0"
    description = "Search for a regex or literal pattern across files in a directory."
    permissions = [ToolPermission.READ]

    async def execute(
        self,
        pattern: str,
        path: str = ".",
        file_glob: str = "**/*",
        regex: bool = True,
        case_sensitive: bool = True,
        max_results: int = 200,
        context_lines: int = 0,
    ) -> ToolResult:
        try:
            safe_dir = _resolve_safe(path)
            if not safe_dir.is_dir():
                return ToolResult(success=False, error=f"Not a directory: {path}")

            flags = 0 if case_sensitive else re.IGNORECASE
            compiled = re.compile(pattern if regex else re.escape(pattern), flags)

            matches: List[Dict[str, Any]] = []
            for file_path in safe_dir.glob(file_glob):
                if not file_path.is_file():
                    continue
                try:
                    async with aiofiles.open(file_path, "r", errors="replace") as f:
                        lines = await f.readlines()
                except Exception:
                    continue

                for lineno, line in enumerate(lines, 1):
                    if compiled.search(line):
                        entry: Dict[str, Any] = {
                            "file": str(file_path.relative_to(safe_dir)),
                            "line": lineno,
                            "content": line.rstrip(),
                        }
                        if context_lines > 0:
                            before = [
                                lines[i].rstrip()
                                for i in range(max(0, lineno - 1 - context_lines), lineno - 1)
                            ]
                            after = [
                                lines[i].rstrip()
                                for i in range(lineno, min(len(lines), lineno + context_lines))
                            ]
                            entry["before"] = before
                            entry["after"] = after
                        matches.append(entry)
                        if len(matches) >= max_results:
                            break
                if len(matches) >= max_results:
                    break

            return ToolResult(
                success=True,
                output=matches,
                metadata={
                    "pattern": pattern,
                    "directory": str(safe_dir),
                    "total_matches": len(matches),
                    "truncated": len(matches) >= max_results,
                },
            )
        except (WorkspaceSecurityError, re.error) as exc:
            return ToolResult(success=False, error=str(exc))


class FindFilesTool(BaseTool):
    name = "find_files"
    version = "1.0.0"
    description = "Find files matching a glob pattern within the workspace."
    permissions = [ToolPermission.READ]

    async def execute(
        self,
        path: str = ".",
        pattern: str = "**/*.py",
        max_results: int = 500,
    ) -> ToolResult:
        try:
            safe_dir = _resolve_safe(path)
            if not safe_dir.is_dir():
                return ToolResult(success=False, error=f"Not a directory: {path}")

            results = []
            for fp in safe_dir.glob(pattern):
                if fp.is_file():
                    results.append({
                        "path": str(fp.relative_to(safe_dir)),
                        "size_bytes": fp.stat().st_size,
                        "suffix": fp.suffix,
                    })
                    if len(results) >= max_results:
                        break

            results.sort(key=lambda x: x["path"])
            return ToolResult(
                success=True,
                output=results,
                metadata={"count": len(results), "directory": str(safe_dir), "pattern": pattern},
            )
        except WorkspaceSecurityError as exc:
            return ToolResult(success=False, error=str(exc))
