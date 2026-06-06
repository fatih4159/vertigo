"""Git integration client using GitPython for repository operations."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from app.core.exceptions import GitOperationError, GitConfirmationRequired, WorkspaceSecurityError
from app.config.settings import settings


class GitClient:
    """High-level async-friendly wrapper around git operations."""

    def __init__(self, repo_path: str) -> None:
        self.repo_path = Path(repo_path).resolve()
        self._validate_path(self.repo_path)

    # ------------------------------------------------------------------
    # Safety
    # ------------------------------------------------------------------

    def _validate_path(self, path: Path) -> None:
        allowed = [Path(d).resolve() for d in settings.ALLOWED_DIRECTORIES]
        # Also allow the workspace root
        allowed.append(Path(settings.WORKSPACE_ROOT).resolve())
        if not any(str(path).startswith(str(a)) for a in allowed):
            raise WorkspaceSecurityError(
                f"Path '{path}' is outside allowed directories",
                {"path": str(path), "allowed": [str(a) for a in allowed]},
            )

    def _run(self, *args: str, cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
        cwd = cwd or self.repo_path
        try:
            result = subprocess.run(
                ["git", *args],
                cwd=str(cwd),
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                raise GitOperationError(
                    f"git {args[0]} failed: {result.stderr.strip()}",
                    {"args": list(args), "stderr": result.stderr, "stdout": result.stdout},
                )
            return result
        except subprocess.TimeoutExpired as exc:
            raise GitOperationError(f"git command timed out: git {' '.join(args)}") from exc
        except FileNotFoundError as exc:
            raise GitOperationError("git executable not found") from exc

    # ------------------------------------------------------------------
    # Repository info
    # ------------------------------------------------------------------

    def is_repo(self) -> bool:
        try:
            self._run("rev-parse", "--git-dir")
            return True
        except GitOperationError:
            return False

    def init(self, initial_branch: str = "main") -> str:
        result = self._run("init", "-b", initial_branch)
        logger.info(f"Git repo initialised at {self.repo_path}")
        return result.stdout.strip()

    def clone(self, url: str, destination: Optional[str] = None, depth: int = 0) -> str:
        args = ["clone"]
        if depth > 0:
            args += ["--depth", str(depth)]
        args.append(url)
        if destination:
            dest = Path(destination).resolve()
            self._validate_path(dest)
            args.append(str(dest))
        result = self._run(*args, cwd=self.repo_path.parent)
        logger.info(f"Cloned {url}")
        return result.stdout.strip()

    def status(self) -> Dict[str, Any]:
        result = self._run("status", "--porcelain", "-u")
        lines = [l for l in result.stdout.splitlines() if l.strip()]
        staged, unstaged, untracked = [], [], []
        for line in lines:
            xy, path = line[:2], line[3:]
            if xy[0] != " " and xy[0] != "?":
                staged.append(path)
            if xy[1] not in (" ", "?"):
                unstaged.append(path)
            if xy == "??":
                untracked.append(path)
        branch = self.current_branch()
        return {
            "branch": branch,
            "staged": staged,
            "unstaged": unstaged,
            "untracked": untracked,
            "clean": len(lines) == 0,
        }

    def current_branch(self) -> str:
        try:
            result = self._run("rev-parse", "--abbrev-ref", "HEAD")
            return result.stdout.strip()
        except GitOperationError:
            return "unknown"

    def log(self, n: int = 20, format: str = "%H|%an|%ae|%s|%ai") -> List[Dict[str, str]]:
        result = self._run("log", f"-{n}", f"--pretty=format:{format}")
        commits = []
        for line in result.stdout.splitlines():
            parts = line.split("|")
            if len(parts) >= 5:
                commits.append({
                    "hash": parts[0],
                    "author": parts[1],
                    "email": parts[2],
                    "subject": parts[3],
                    "date": parts[4],
                })
        return commits

    def diff(self, staged: bool = False, file_path: Optional[str] = None) -> str:
        args = ["diff"]
        if staged:
            args.append("--cached")
        if file_path:
            args += ["--", file_path]
        result = self._run(*args)
        return result.stdout

    def show(self, ref: str = "HEAD") -> str:
        result = self._run("show", ref)
        return result.stdout

    # ------------------------------------------------------------------
    # Staging & committing
    # ------------------------------------------------------------------

    def add(self, paths: Optional[List[str]] = None) -> str:
        if paths:
            validated = []
            for p in paths:
                fp = Path(p).resolve() if Path(p).is_absolute() else (self.repo_path / p).resolve()
                self._validate_path(fp)
                validated.append(str(fp))
            result = self._run("add", *validated)
        else:
            result = self._run("add", "-A")
        return result.stdout.strip()

    def commit(
        self,
        message: str,
        author_name: str = "AAOS Agent",
        author_email: str = "agent@aaos.local",
        require_confirmation: bool = False,
    ) -> str:
        if require_confirmation:
            raise GitConfirmationRequired(
                "Commit requires user confirmation",
                {"message": message, "action": "commit"},
            )
        env = os.environ.copy()
        env["GIT_AUTHOR_NAME"] = author_name
        env["GIT_AUTHOR_EMAIL"] = author_email
        env["GIT_COMMITTER_NAME"] = author_name
        env["GIT_COMMITTER_EMAIL"] = author_email
        result = subprocess.run(
            ["git", "commit", "-m", message],
            cwd=str(self.repo_path),
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
        )
        if result.returncode != 0:
            raise GitOperationError(f"Commit failed: {result.stderr}", {"stderr": result.stderr})
        logger.info(f"Committed: {message[:60]}")
        return result.stdout.strip()

    # ------------------------------------------------------------------
    # Branches
    # ------------------------------------------------------------------

    def list_branches(self, remote: bool = False) -> List[str]:
        args = ["branch"]
        if remote:
            args.append("-r")
        result = self._run(*args)
        return [b.strip().lstrip("* ") for b in result.stdout.splitlines() if b.strip()]

    def create_branch(self, name: str, checkout: bool = True) -> str:
        if checkout:
            result = self._run("checkout", "-b", name)
        else:
            result = self._run("branch", name)
        logger.info(f"Created branch: {name}")
        return result.stdout.strip()

    def checkout(self, ref: str) -> str:
        result = self._run("checkout", ref)
        return result.stdout.strip()

    def merge(self, branch: str, message: Optional[str] = None, require_confirmation: bool = True) -> str:
        if require_confirmation:
            raise GitConfirmationRequired(
                "Merge requires user confirmation",
                {"branch": branch, "action": "merge"},
            )
        args = ["merge", "--no-ff", branch]
        if message:
            args += ["-m", message]
        result = self._run(*args)
        return result.stdout.strip()

    # ------------------------------------------------------------------
    # Remote operations (require confirmation by default)
    # ------------------------------------------------------------------

    def fetch(self, remote: str = "origin", branch: Optional[str] = None) -> str:
        args = ["fetch", remote]
        if branch:
            args.append(branch)
        result = self._run(*args)
        return result.stdout.strip()

    def pull(self, remote: str = "origin", branch: Optional[str] = None, require_confirmation: bool = True) -> str:
        if require_confirmation:
            raise GitConfirmationRequired(
                "Pull requires user confirmation",
                {"remote": remote, "action": "pull"},
            )
        args = ["pull", remote]
        if branch:
            args.append(branch)
        result = self._run(*args)
        return result.stdout.strip()

    def push(
        self,
        remote: str = "origin",
        branch: Optional[str] = None,
        force: bool = False,
        require_confirmation: bool = True,
    ) -> str:
        if require_confirmation:
            raise GitConfirmationRequired(
                "Push requires user confirmation",
                {"remote": remote, "force": force, "action": "push"},
            )
        if force:
            raise GitOperationError("Force push is disabled for safety. Use Git client directly.")
        args = ["push", remote]
        if branch:
            args.append(branch)
        result = self._run(*args)
        return result.stdout.strip()

    # ------------------------------------------------------------------
    # Stash
    # ------------------------------------------------------------------

    def stash(self, message: str = "") -> str:
        args = ["stash", "push"]
        if message:
            args += ["-m", message]
        result = self._run(*args)
        return result.stdout.strip()

    def stash_pop(self) -> str:
        result = self._run("stash", "pop")
        return result.stdout.strip()

    def stash_list(self) -> List[str]:
        result = self._run("stash", "list")
        return result.stdout.splitlines()

    # ------------------------------------------------------------------
    # Tags
    # ------------------------------------------------------------------

    def list_tags(self) -> List[str]:
        result = self._run("tag")
        return [t.strip() for t in result.stdout.splitlines() if t.strip()]

    def create_tag(self, name: str, message: str = "", ref: str = "HEAD") -> str:
        if message:
            result = self._run("tag", "-a", name, "-m", message, ref)
        else:
            result = self._run("tag", name, ref)
        return result.stdout.strip()

    # ------------------------------------------------------------------
    # File operations
    # ------------------------------------------------------------------

    def file_blame(self, file_path: str) -> str:
        result = self._run("blame", file_path)
        return result.stdout

    def file_history(self, file_path: str, n: int = 20) -> List[Dict[str, str]]:
        result = self._run("log", f"-{n}", "--follow", "--pretty=format:%H|%an|%s|%ai", "--", file_path)
        history = []
        for line in result.stdout.splitlines():
            parts = line.split("|")
            if len(parts) >= 4:
                history.append({"hash": parts[0], "author": parts[1], "subject": parts[2], "date": parts[3]})
        return history

    def to_dict(self) -> Dict[str, Any]:
        """Summarise repository state."""
        try:
            st = self.status()
            log = self.log(n=5)
            return {"path": str(self.repo_path), "status": st, "recent_commits": log}
        except GitOperationError as exc:
            return {"path": str(self.repo_path), "error": str(exc)}
