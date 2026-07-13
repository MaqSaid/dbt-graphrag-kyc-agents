"""Code quality assertion tests.

Programmatically executes ruff and mypy as subprocess assertions,
validating that the codebase adheres to defined formatting and type guidelines.
"""

from __future__ import annotations

import subprocess
import sys

import pytest


class TestRuffLinting:
    """Tests that Ruff linting passes with zero violations."""

    def test_ruff_check_passes(self) -> None:
        """All source code must pass Ruff linting without errors."""
        result = subprocess.run(
            [sys.executable, "-m", "ruff", "check", "src/", "--quiet"],
            capture_output=True,
            text=True,
            cwd=str(_project_root()),
        )
        if result.returncode != 0:
            pytest.fail(
                f"Ruff linting failed with {result.stdout.count(chr(10))} violation(s):\n"
                f"{result.stdout[:2000]}"
            )

    def test_ruff_format_check(self) -> None:
        """All source code must be properly formatted by Ruff."""
        result = subprocess.run(
            [sys.executable, "-m", "ruff", "format", "--check", "src/"],
            capture_output=True,
            text=True,
            cwd=str(_project_root()),
        )
        if result.returncode != 0:
            pytest.fail(
                f"Ruff formatting check failed. Files need formatting:\n"
                f"{result.stdout[:2000]}"
            )


class TestMypyTypeChecking:
    """Tests that Mypy type checking passes in strict mode."""

    @pytest.mark.slow
    def test_mypy_strict_passes(self) -> None:
        """All source code must pass Mypy strict type checking.

        Note: This test is marked slow as Mypy analysis takes time.
        """
        result = subprocess.run(
            [sys.executable, "-m", "mypy", "src/", "--strict", "--ignore-missing-imports"],
            capture_output=True,
            text=True,
            cwd=str(_project_root()),
        )
        if result.returncode != 0:
            error_count = result.stdout.count("error:")
            pytest.fail(
                f"Mypy strict checking failed with {error_count} error(s):\n"
                f"{result.stdout[:3000]}"
            )


def _project_root():
    """Get the project root directory."""
    from pathlib import Path
    return Path(__file__).parent.parent.parent
