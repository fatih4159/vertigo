"""Code editor tool - apply targeted edits and patches to source files."""
from __future__ import annotations

import difflib
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiofiles

from app.tools.base import BaseTool, ToolPermission, ToolResult
from app.tools.filesystem import _resolve_safe
from app.core.exceptions import WorkspaceSecurityError


class InsertCodeTool(BaseTool):
    name = "insert_code"
    version = "1.0.0"
    description = "Insert code at a specific line number in a file."
    permissions = [ToolPermission.READ, ToolPermission.WRITE]

    async def execute(self, path: str, line_number: int, code: str) -> ToolResult:
        try:
            safe_path = _resolve_safe(path)
            if not safe_path.exists():
                return ToolResult(success=False, error=f"File not found: {path}")
            async with aiofiles.open(safe_path, "r") as f:
                lines = await f.readlines()
            idx = max(0, min(line_number - 1, len(lines)))
            new_lines = lines[:idx] + [code + "\n"] + lines[idx:]
            async with aiofiles.open(safe_path, "w") as f:
                await f.writelines(new_lines)
            return ToolResult(
                success=True,
                output=f"Inserted code at line {line_number} in {safe_path}",
            )
        except WorkspaceSecurityError as exc:
            return ToolResult(success=False, error=str(exc))


class ReplaceCodeTool(BaseTool):
    name = "replace_code"
    version = "1.0.0"
    description = (
        "Replace an exact block of text in a file with new content. "
        "Uses exact string matching — old_code must appear verbatim."
    )
    permissions = [ToolPermission.READ, ToolPermission.WRITE]

    async def execute(self, path: str, old_code: str, new_code: str) -> ToolResult:
        try:
            safe_path = _resolve_safe(path)
            if not safe_path.exists():
                return ToolResult(success=False, error=f"File not found: {path}")
            async with aiofiles.open(safe_path, "r") as f:
                content = await f.read()
            if old_code not in content:
                return ToolResult(
                    success=False,
                    error="old_code not found in file. Check exact whitespace and indentation.",
                    metadata={"path": str(safe_path)},
                )
            count = content.count(old_code)
            if count > 1:
                return ToolResult(
                    success=False,
                    error=f"old_code appears {count} times; provide more context to make it unique.",
                )
            new_content = content.replace(old_code, new_code, 1)
            async with aiofiles.open(safe_path, "w") as f:
                await f.write(new_content)
            diff = list(
                difflib.unified_diff(
                    content.splitlines(keepends=True),
                    new_content.splitlines(keepends=True),
                    fromfile=f"a/{safe_path.name}",
                    tofile=f"b/{safe_path.name}",
                    n=3,
                )
            )
            return ToolResult(
                success=True,
                output="".join(diff[:200]),
                metadata={"path": str(safe_path), "diff_lines": len(diff)},
            )
        except WorkspaceSecurityError as exc:
            return ToolResult(success=False, error=str(exc))


class DeleteLinesTools(BaseTool):
    name = "delete_lines"
    version = "1.0.0"
    description = "Delete a range of lines from a file (1-indexed, inclusive)."
    permissions = [ToolPermission.READ, ToolPermission.WRITE]

    async def execute(self, path: str, start_line: int, end_line: int) -> ToolResult:
        try:
            safe_path = _resolve_safe(path)
            if not safe_path.exists():
                return ToolResult(success=False, error=f"File not found: {path}")
            async with aiofiles.open(safe_path, "r") as f:
                lines = await f.readlines()
            if start_line < 1 or end_line > len(lines):
                return ToolResult(
                    success=False,
                    error=f"Line range [{start_line},{end_line}] out of bounds (file has {len(lines)} lines)",
                )
            del lines[start_line - 1 : end_line]
            async with aiofiles.open(safe_path, "w") as f:
                await f.writelines(lines)
            return ToolResult(
                success=True,
                output=f"Deleted lines {start_line}-{end_line} from {safe_path}",
            )
        except WorkspaceSecurityError as exc:
            return ToolResult(success=False, error=str(exc))


class ApplyPatchTool(BaseTool):
    name = "apply_patch"
    version = "1.0.0"
    description = "Apply a unified diff patch string to a file."
    permissions = [ToolPermission.READ, ToolPermission.WRITE]

    async def execute(self, path: str, patch: str) -> ToolResult:
        """Very simplified patch applicator — handles @@-based hunks."""
        try:
            safe_path = _resolve_safe(path)
            if not safe_path.exists():
                return ToolResult(success=False, error=f"File not found: {path}")
            async with aiofiles.open(safe_path, "r") as f:
                original = await f.read()
            lines = original.splitlines(keepends=True)
            patch_lines = patch.splitlines(keepends=True)

            # Parse and apply hunks
            result_lines = list(lines)
            offset = 0
            hunk_header = re.compile(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
            i = 0
            while i < len(patch_lines):
                m = hunk_header.match(patch_lines[i])
                if m:
                    orig_start = int(m.group(1)) - 1
                    orig_count = int(m.group(2)) if m.group(2) else 1
                    i += 1
                    hunk_remove: List[str] = []
                    hunk_add: List[str] = []
                    while i < len(patch_lines) and not hunk_header.match(patch_lines[i]):
                        pl = patch_lines[i]
                        if pl.startswith("-"):
                            hunk_remove.append(pl[1:])
                        elif pl.startswith("+"):
                            hunk_add.append(pl[1:])
                        elif pl.startswith(" "):
                            hunk_remove.append(pl[1:])
                            hunk_add.append(pl[1:])
                        i += 1
                    start = orig_start + offset
                    end = start + len(hunk_remove)
                    result_lines[start:end] = hunk_add
                    offset += len(hunk_add) - len(hunk_remove)
                else:
                    i += 1

            new_content = "".join(result_lines)
            async with aiofiles.open(safe_path, "w") as f:
                await f.write(new_content)
            return ToolResult(
                success=True,
                output=f"Patch applied to {safe_path}",
            )
        except WorkspaceSecurityError as exc:
            return ToolResult(success=False, error=str(exc))
        except Exception as exc:
            return ToolResult(success=False, error=f"Patch failed: {exc}")


class SearchInFileTool(BaseTool):
    name = "search_in_file"
    version = "1.0.0"
    description = "Search for a pattern (regex or literal) within a file and return matching lines."
    permissions = [ToolPermission.READ]

    async def execute(
        self, path: str, pattern: str, regex: bool = False, case_sensitive: bool = True
    ) -> ToolResult:
        try:
            safe_path = _resolve_safe(path)
            if not safe_path.exists():
                return ToolResult(success=False, error=f"File not found: {path}")
            async with aiofiles.open(safe_path, "r") as f:
                lines = await f.readlines()
            matches = []
            flags = 0 if case_sensitive else re.IGNORECASE
            for lineno, line in enumerate(lines, 1):
                hit = re.search(pattern, line, flags) if regex else (
                    (pattern in line) if case_sensitive else (pattern.lower() in line.lower())
                )
                if hit:
                    matches.append({"line": lineno, "content": line.rstrip()})
            return ToolResult(
                success=True,
                output=matches,
                metadata={"total_matches": len(matches), "file": str(safe_path)},
            )
        except (WorkspaceSecurityError, re.error) as exc:
            return ToolResult(success=False, error=str(exc))
