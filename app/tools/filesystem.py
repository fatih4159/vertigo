"""Filesystem tool - safe read/write/list within allowed directories."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiofiles
from loguru import logger

from app.tools.base import BaseTool, ToolPermission, ToolResult
from app.config.settings import settings
from app.core.exceptions import WorkspaceSecurityError


def _resolve_safe(path: str) -> Path:
    """Resolve path and verify it sits inside an allowed directory."""
    resolved = Path(path).resolve()
    allowed = [Path(d).resolve() for d in settings.ALLOWED_DIRECTORIES]
    allowed.append(Path(settings.WORKSPACE_ROOT).resolve())
    if not any(str(resolved).startswith(str(a)) for a in allowed):
        raise WorkspaceSecurityError(
            f"Access denied: '{resolved}' is outside allowed directories",
            {"path": str(resolved)},
        )
    return resolved


class ReadFileTool(BaseTool):
    name = "read_file"
    version = "1.0.0"
    description = "Read the contents of a file within the workspace."
    permissions = [ToolPermission.READ]

    async def execute(self, path: str, encoding: str = "utf-8") -> ToolResult:
        try:
            safe_path = _resolve_safe(path)
            if not safe_path.exists():
                return ToolResult(success=False, error=f"File not found: {path}")
            if not safe_path.is_file():
                return ToolResult(success=False, error=f"Not a file: {path}")
            async with aiofiles.open(safe_path, "r", encoding=encoding) as f:
                content = await f.read()
            return ToolResult(
                success=True,
                output=content,
                metadata={"path": str(safe_path), "size_bytes": safe_path.stat().st_size},
            )
        except WorkspaceSecurityError as exc:
            return ToolResult(success=False, error=str(exc))
        except UnicodeDecodeError:
            return ToolResult(success=False, error=f"Cannot decode file as {encoding}: {path}")

    def _parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path to read"},
                "encoding": {"type": "string", "default": "utf-8"},
            },
            "required": ["path"],
        }


class WriteFileTool(BaseTool):
    name = "write_file"
    version = "1.0.0"
    description = "Write content to a file within the workspace. Creates parent directories as needed."
    permissions = [ToolPermission.WRITE]

    async def execute(
        self, path: str, content: str, encoding: str = "utf-8", overwrite: bool = True
    ) -> ToolResult:
        try:
            safe_path = _resolve_safe(path)
            if safe_path.exists() and not overwrite:
                return ToolResult(success=False, error=f"File already exists and overwrite=False: {path}")
            safe_path.parent.mkdir(parents=True, exist_ok=True)
            async with aiofiles.open(safe_path, "w", encoding=encoding) as f:
                await f.write(content)
            return ToolResult(
                success=True,
                output=f"Written {len(content)} chars to {safe_path}",
                metadata={"path": str(safe_path), "bytes_written": len(content.encode(encoding))},
            )
        except WorkspaceSecurityError as exc:
            return ToolResult(success=False, error=str(exc))

    def _parameters_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
                "encoding": {"type": "string", "default": "utf-8"},
                "overwrite": {"type": "boolean", "default": True},
            },
            "required": ["path", "content"],
        }


class AppendFileTool(BaseTool):
    name = "append_file"
    version = "1.0.0"
    description = "Append content to an existing file."
    permissions = [ToolPermission.WRITE]

    async def execute(self, path: str, content: str, encoding: str = "utf-8") -> ToolResult:
        try:
            safe_path = _resolve_safe(path)
            safe_path.parent.mkdir(parents=True, exist_ok=True)
            async with aiofiles.open(safe_path, "a", encoding=encoding) as f:
                await f.write(content)
            return ToolResult(
                success=True,
                output=f"Appended {len(content)} chars to {safe_path}",
                metadata={"path": str(safe_path)},
            )
        except WorkspaceSecurityError as exc:
            return ToolResult(success=False, error=str(exc))


class ListDirectoryTool(BaseTool):
    name = "list_directory"
    version = "1.0.0"
    description = "List files and directories in a path."
    permissions = [ToolPermission.READ]

    async def execute(
        self, path: str = ".", recursive: bool = False, pattern: str = "*"
    ) -> ToolResult:
        try:
            safe_path = _resolve_safe(path)
            if not safe_path.exists():
                return ToolResult(success=False, error=f"Directory not found: {path}")
            if not safe_path.is_dir():
                return ToolResult(success=False, error=f"Not a directory: {path}")

            entries = []
            if recursive:
                for item in safe_path.rglob(pattern):
                    entries.append({
                        "path": str(item.relative_to(safe_path)),
                        "type": "file" if item.is_file() else "dir",
                        "size": item.stat().st_size if item.is_file() else None,
                    })
            else:
                for item in safe_path.glob(pattern):
                    entries.append({
                        "path": item.name,
                        "type": "file" if item.is_file() else "dir",
                        "size": item.stat().st_size if item.is_file() else None,
                    })

            entries.sort(key=lambda e: (e["type"], e["path"]))
            return ToolResult(
                success=True,
                output=entries,
                metadata={"directory": str(safe_path), "count": len(entries)},
            )
        except WorkspaceSecurityError as exc:
            return ToolResult(success=False, error=str(exc))


class DeleteFileTool(BaseTool):
    name = "delete_file"
    version = "1.0.0"
    description = "Delete a file (not directories) from the workspace."
    permissions = [ToolPermission.WRITE]

    async def execute(self, path: str) -> ToolResult:
        try:
            safe_path = _resolve_safe(path)
            if not safe_path.exists():
                return ToolResult(success=False, error=f"File not found: {path}")
            if not safe_path.is_file():
                return ToolResult(success=False, error="Only individual files can be deleted.")
            safe_path.unlink()
            return ToolResult(success=True, output=f"Deleted: {safe_path}")
        except WorkspaceSecurityError as exc:
            return ToolResult(success=False, error=str(exc))


class MakeDirectoryTool(BaseTool):
    name = "make_directory"
    version = "1.0.0"
    description = "Create a directory (and parents) within the workspace."
    permissions = [ToolPermission.WRITE]

    async def execute(self, path: str) -> ToolResult:
        try:
            safe_path = _resolve_safe(path)
            safe_path.mkdir(parents=True, exist_ok=True)
            return ToolResult(success=True, output=f"Directory created: {safe_path}")
        except WorkspaceSecurityError as exc:
            return ToolResult(success=False, error=str(exc))


class MoveFileTool(BaseTool):
    name = "move_file"
    version = "1.0.0"
    description = "Move or rename a file within the workspace."
    permissions = [ToolPermission.WRITE]

    async def execute(self, source: str, destination: str) -> ToolResult:
        try:
            src = _resolve_safe(source)
            dst = _resolve_safe(destination)
            if not src.exists():
                return ToolResult(success=False, error=f"Source not found: {source}")
            dst.parent.mkdir(parents=True, exist_ok=True)
            src.rename(dst)
            return ToolResult(success=True, output=f"Moved {src} -> {dst}")
        except WorkspaceSecurityError as exc:
            return ToolResult(success=False, error=str(exc))


class FileStatsTool(BaseTool):
    name = "file_stats"
    version = "1.0.0"
    description = "Return metadata/stats for a file or directory."
    permissions = [ToolPermission.READ]

    async def execute(self, path: str) -> ToolResult:
        try:
            safe_path = _resolve_safe(path)
            if not safe_path.exists():
                return ToolResult(success=False, error=f"Path not found: {path}")
            stat = safe_path.stat()
            info: Dict[str, Any] = {
                "path": str(safe_path),
                "exists": True,
                "type": "file" if safe_path.is_file() else "dir",
                "size_bytes": stat.st_size,
                "modified_at": stat.st_mtime,
                "suffix": safe_path.suffix,
            }
            if safe_path.is_file():
                try:
                    async with aiofiles.open(safe_path, "r") as f:
                        content = await f.read()
                    info["line_count"] = content.count("\n") + 1
                    info["char_count"] = len(content)
                except Exception:
                    pass
            return ToolResult(success=True, output=info)
        except WorkspaceSecurityError as exc:
            return ToolResult(success=False, error=str(exc))
