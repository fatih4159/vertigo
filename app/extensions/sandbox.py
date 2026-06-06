"""Safe sandbox for validating generated code.

Runs generated Python code in a subprocess with a strict timeout,
checks for forbidden patterns, and optionally executes generated unit tests.
"""
from __future__ import annotations

import ast
import re
import subprocess
import sys
import tempfile
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from loguru import logger


# Patterns that indicate unsafe code
_FORBIDDEN_PATTERNS: List[tuple[str, str]] = [
    (r"subprocess\..*shell\s*=\s*True", "subprocess with shell=True"),
    (r"os\.system\s*\(", "os.system()"),
    (r"eval\s*\(", "eval()"),
    (r"exec\s*\(", "exec()"),
    (r"__import__\s*\(", "dynamic __import__()"),
    (r"open\s*\(.*['\"]w['\"]", "file write via open()"),
    (r"shutil\.(rmtree|move|copytree)", "destructive shutil operations"),
    (r"socket\.socket", "raw socket access"),
    (r"ctypes", "ctypes usage"),
    (r"importlib\.import_module.*os", "dynamic os import"),
]

_FORBIDDEN_IMPORTS: set[str] = {
    "pty",
    "tty",
    "termios",
    "fcntl",
    "signal",
    "multiprocessing",
}


@dataclass
class ValidationResult:
    """Result of validating generated code in the sandbox."""

    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    test_output: Optional[str] = None
    syntax_ok: bool = True

    @property
    def summary(self) -> str:
        if self.is_valid:
            return "Validation passed"
        return "Validation failed: " + "; ".join(self.errors)


class Sandbox:
    """Validates generated Python code safely."""

    def __init__(self, timeout: int = 10) -> None:
        self.timeout = timeout

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate(self, code: str, test_code: Optional[str] = None) -> ValidationResult:
        """
        Full validation pipeline:
        1. Static pattern checks
        2. AST syntax check
        3. Forbidden import check via AST
        4. Optional subprocess test run
        """
        result = ValidationResult(is_valid=True)

        # 1. Static pattern scan
        self._check_forbidden_patterns(code, result)

        # 2. Syntax check
        if not self._check_syntax(code, result):
            return result  # No point going further

        # 3. AST import check
        self._check_forbidden_imports(code, result)

        if not result.is_valid:
            return result

        # 4. Test run
        if test_code:
            self._run_tests(code, test_code, result)

        return result

    def validate_syntax_only(self, code: str) -> ValidationResult:
        """Lightweight check: syntax + forbidden patterns only."""
        result = ValidationResult(is_valid=True)
        self._check_forbidden_patterns(code, result)
        self._check_syntax(code, result)
        return result

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _check_forbidden_patterns(self, code: str, result: ValidationResult) -> None:
        for pattern, description in _FORBIDDEN_PATTERNS:
            if re.search(pattern, code):
                result.is_valid = False
                result.errors.append(f"Forbidden pattern: {description}")
                logger.warning(f"Sandbox rejected code: {description}")

    def _check_syntax(self, code: str, result: ValidationResult) -> bool:
        try:
            ast.parse(code)
            return True
        except SyntaxError as e:
            result.is_valid = False
            result.syntax_ok = False
            result.errors.append(f"SyntaxError at line {e.lineno}: {e.msg}")
            logger.warning(f"Sandbox syntax check failed: {e}")
            return False

    def _check_forbidden_imports(self, code: str, result: ValidationResult) -> None:
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return

        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.Import):
                    names = [alias.name.split(".")[0] for alias in node.names]
                else:
                    names = [node.module.split(".")[0]] if node.module else []

                for name in names:
                    if name in _FORBIDDEN_IMPORTS:
                        result.is_valid = False
                        result.errors.append(f"Forbidden import: {name}")

    def _run_tests(self, code: str, test_code: str, result: ValidationResult) -> None:
        """Run tests in an isolated subprocess."""
        full_code = textwrap.dedent(f"""
{code}

# ---- Generated Tests ----
{test_code}

if __name__ == '__main__':
    import unittest
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(__import__('__main__'))
    runner = unittest.TextTestRunner(verbosity=2)
    test_result = runner.run(suite)
    exit(0 if test_result.wasSuccessful() else 1)
""")
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as f:
            f.write(full_code)
            tmp_path = f.name

        try:
            proc = subprocess.run(
                [sys.executable, tmp_path],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env={
                    "PATH": "/usr/bin:/bin",
                    "PYTHONPATH": "",
                },
            )
            result.test_output = proc.stdout + proc.stderr
            if proc.returncode != 0:
                result.is_valid = False
                result.errors.append(
                    f"Tests failed (exit {proc.returncode}): {proc.stderr[:500]}"
                )
                logger.warning(f"Sandbox test run failed: {proc.stderr[:200]}")
            else:
                logger.info("Sandbox test run passed")
        except subprocess.TimeoutExpired:
            result.is_valid = False
            result.errors.append(f"Test execution timed out after {self.timeout}s")
            logger.warning("Sandbox execution timed out")
        finally:
            Path(tmp_path).unlink(missing_ok=True)
