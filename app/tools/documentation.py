"""Documentation tool - generate and read project documentation."""
from __future__ import annotations

import ast
import textwrap
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiofiles

from app.tools.base import BaseTool, ToolPermission, ToolResult
from app.tools.filesystem import _resolve_safe
from app.core.exceptions import WorkspaceSecurityError


class ExtractDocstringsTool(BaseTool):
    name = "extract_docstrings"
    version = "1.0.0"
    description = "Extract all docstrings from a Python file."
    permissions = [ToolPermission.READ]

    async def execute(self, path: str) -> ToolResult:
        try:
            safe_path = _resolve_safe(path)
            if not safe_path.exists():
                return ToolResult(success=False, error=f"File not found: {path}")
            async with aiofiles.open(safe_path, "r") as f:
                source = await f.read()
            try:
                tree = ast.parse(source)
            except SyntaxError as exc:
                return ToolResult(success=False, error=f"Syntax error: {exc}")

            docs = []
            for node in ast.walk(tree):
                if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    docstring = ast.get_docstring(node)
                    if docstring:
                        docs.append({
                            "type": type(node).__name__,
                            "name": getattr(node, "name", "<module>"),
                            "line": getattr(node, "lineno", 0),
                            "docstring": docstring,
                        })

            return ToolResult(
                success=True,
                output=docs,
                metadata={"file": str(safe_path), "count": len(docs)},
            )
        except WorkspaceSecurityError as exc:
            return ToolResult(success=False, error=str(exc))


class GenerateMarkdownDocTool(BaseTool):
    name = "generate_markdown_doc"
    version = "1.0.0"
    description = "Generate a Markdown documentation file for a Python module."
    permissions = [ToolPermission.READ, ToolPermission.WRITE]

    async def execute(
        self, source_path: str, output_path: Optional[str] = None
    ) -> ToolResult:
        try:
            safe_src = _resolve_safe(source_path)
            if not safe_src.exists():
                return ToolResult(success=False, error=f"File not found: {source_path}")
            async with aiofiles.open(safe_src, "r") as f:
                source = await f.read()

            try:
                tree = ast.parse(source)
            except SyntaxError as exc:
                return ToolResult(success=False, error=f"Syntax error: {exc}")

            lines = [f"# {safe_src.stem}\n"]
            module_doc = ast.get_docstring(tree)
            if module_doc:
                lines.append(f"\n{module_doc}\n")

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    lines.append(f"\n## class `{node.name}`\n")
                    class_doc = ast.get_docstring(node)
                    if class_doc:
                        lines.append(f"{class_doc}\n")
                    for item in node.body:
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            sig = self._signature(item)
                            lines.append(f"\n### `{sig}`\n")
                            fn_doc = ast.get_docstring(item)
                            if fn_doc:
                                lines.append(f"{fn_doc}\n")

                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # Top-level functions only
                    sig = self._signature(node)
                    lines.append(f"\n## `{sig}`\n")
                    fn_doc = ast.get_docstring(node)
                    if fn_doc:
                        lines.append(f"{fn_doc}\n")

            markdown = "\n".join(lines)

            if output_path:
                safe_out = _resolve_safe(output_path)
                safe_out.parent.mkdir(parents=True, exist_ok=True)
                async with aiofiles.open(safe_out, "w") as f:
                    await f.write(markdown)
                return ToolResult(
                    success=True,
                    output=f"Documentation written to {safe_out}",
                    metadata={"source": str(safe_src), "output": str(safe_out)},
                )
            return ToolResult(success=True, output=markdown)

        except WorkspaceSecurityError as exc:
            return ToolResult(success=False, error=str(exc))

    def _signature(self, node: Any) -> str:
        name = node.name
        args = []
        defaults = [None] * (len(node.args.args) - len(node.args.defaults)) + list(node.args.defaults)
        for arg, default in zip(node.args.args, defaults):
            ann = f": {ast.unparse(arg.annotation)}" if arg.annotation else ""
            val = f" = {ast.unparse(default)}" if default else ""
            args.append(f"{arg.arg}{ann}{val}")
        ret = f" -> {ast.unparse(node.returns)}" if node.returns else ""
        prefix = "async " if isinstance(node, ast.AsyncFunctionDef) else ""
        return f"{prefix}{name}({', '.join(args)}){ret}"


class ReadDocumentationTool(BaseTool):
    name = "read_documentation"
    version = "1.0.0"
    description = "Read a documentation or README file from the workspace."
    permissions = [ToolPermission.READ]

    async def execute(self, path: str) -> ToolResult:
        try:
            safe_path = _resolve_safe(path)
            if not safe_path.exists():
                return ToolResult(success=False, error=f"File not found: {path}")
            async with aiofiles.open(safe_path, "r") as f:
                content = await f.read()
            return ToolResult(
                success=True,
                output=content,
                metadata={"path": str(safe_path), "size_chars": len(content)},
            )
        except WorkspaceSecurityError as exc:
            return ToolResult(success=False, error=str(exc))
