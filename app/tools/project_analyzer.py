"""Project analyzer tool - structural analysis of a code project."""
from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiofiles

from app.tools.base import BaseTool, ToolPermission, ToolResult
from app.tools.filesystem import _resolve_safe
from app.core.exceptions import WorkspaceSecurityError


class ProjectAnalyzerTool(BaseTool):
    name = "project_analyzer"
    version = "1.0.0"
    description = (
        "Analyse a code project's structure: file tree, language breakdown, "
        "Python module imports, and high-level statistics."
    )
    permissions = [ToolPermission.READ]

    def _parameters_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Absolute or workspace-relative path to the project directory to analyse",
                },
                "max_files": {
                    "type": "integer",
                    "description": "Maximum number of files to inspect (default 1000)",
                },
            },
            "required": ["path"],
        }

    async def execute(self, path: str, max_files: int = 1000) -> ToolResult:
        try:
            root = _resolve_safe(path)
            if not root.is_dir():
                return ToolResult(success=False, error=f"Not a directory: {path}")

            stats: Dict[str, Any] = {
                "root": str(root),
                "file_count": 0,
                "dir_count": 0,
                "total_size_bytes": 0,
                "languages": {},
                "python": {"modules": [], "imports": set(), "classes": [], "functions": []},
                "config_files": [],
                "tree": [],
            }

            EXT_LANG = {
                ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
                ".jsx": "React/JSX", ".tsx": "React/TSX", ".go": "Go",
                ".rs": "Rust", ".java": "Java", ".cpp": "C++", ".c": "C",
                ".sh": "Shell", ".yaml": "YAML", ".yml": "YAML",
                ".json": "JSON", ".toml": "TOML", ".md": "Markdown",
                ".html": "HTML", ".css": "CSS", ".sql": "SQL",
            }
            CONFIG_NAMES = {
                "pyproject.toml", "setup.py", "setup.cfg", "requirements.txt",
                "package.json", "tsconfig.json", "Makefile", "Dockerfile",
                ".env.example", "alembic.ini", "pytest.ini", ".gitignore",
            }

            file_count = 0
            for item in root.rglob("*"):
                # Skip hidden dirs and common noise
                parts = item.relative_to(root).parts
                if any(p.startswith(".") or p in ("__pycache__", "node_modules", ".git", "venv", ".venv") for p in parts):
                    continue

                if item.is_dir():
                    stats["dir_count"] += 1
                    continue

                if file_count >= max_files:
                    break

                file_count += 1
                stats["file_count"] += 1
                try:
                    size = item.stat().st_size
                except OSError:
                    size = 0
                stats["total_size_bytes"] += size

                rel_path = str(item.relative_to(root))
                lang = EXT_LANG.get(item.suffix, "Other")
                stats["languages"][lang] = stats["languages"].get(lang, 0) + 1

                if item.name in CONFIG_NAMES:
                    stats["config_files"].append(rel_path)

                stats["tree"].append({"path": rel_path, "size": size, "lang": lang})

                # Deep Python analysis
                if item.suffix == ".py" and size < 500_000:
                    try:
                        async with aiofiles.open(item, "r", errors="replace") as f:
                            source = await f.read()
                        tree = ast.parse(source, filename=rel_path)
                        imports_in_file = set()
                        classes_in_file = []
                        functions_in_file = []
                        for node in ast.walk(tree):
                            if isinstance(node, ast.Import):
                                for alias in node.names:
                                    imports_in_file.add(alias.name.split(".")[0])
                            elif isinstance(node, ast.ImportFrom):
                                if node.module:
                                    imports_in_file.add(node.module.split(".")[0])
                            elif isinstance(node, ast.ClassDef):
                                classes_in_file.append({"name": node.name, "file": rel_path, "line": node.lineno})
                            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                                if not isinstance(getattr(node, "parent", None), ast.ClassDef):
                                    functions_in_file.append({"name": node.name, "file": rel_path, "line": node.lineno})
                        stats["python"]["imports"].update(imports_in_file)
                        stats["python"]["classes"].extend(classes_in_file)
                        stats["python"]["functions"].extend(functions_in_file)
                        stats["python"]["modules"].append(rel_path)
                    except SyntaxError:
                        pass
                    except Exception:
                        pass

            stats["python"]["imports"] = sorted(stats["python"]["imports"])

            # Detect project type
            project_type = "unknown"
            config_set = set(stats["config_files"])
            if any("requirements.txt" in c or "pyproject.toml" in c for c in config_set):
                project_type = "Python"
            if any("package.json" in c for c in config_set):
                project_type = "Node.js"

            stats["project_type"] = project_type
            stats["summary"] = (
                f"{stats['file_count']} files, {stats['dir_count']} dirs, "
                f"{stats['total_size_bytes'] // 1024}KB total — {project_type} project"
            )

            return ToolResult(
                success=True,
                output=stats,
                metadata={"root": str(root)},
            )
        except WorkspaceSecurityError as exc:
            return ToolResult(success=False, error=str(exc))
