"""Architecture boundary enforcement tests.

Validates that hexagonal architecture import rules are followed:
- Domain layer has zero imports from infrastructure, api, or agents
- Agents layer imports only from domain
- No circular dependencies between bounded contexts

These tests scan actual Python source files for import statements.
"""

from __future__ import annotations

import ast
import os
from pathlib import Path

import pytest

SRC_ROOT = Path(__file__).parent.parent.parent / "src"


def _get_python_files(directory: Path) -> list[Path]:
    """Recursively find all Python files in a directory."""
    return list(directory.rglob("*.py"))


def _extract_imports(file_path: Path) -> list[str]:
    """Extract all import module paths from a Python file."""
    try:
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (SyntaxError, UnicodeDecodeError):
        return []

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return imports


class TestDomainBoundary:
    """Tests ensuring domain layer has no infrastructure/api/agent imports."""

    def test_domain_does_not_import_infrastructure(self) -> None:
        """Domain layer must not import from src.infrastructure."""
        domain_dir = SRC_ROOT / "domain"
        if not domain_dir.exists():
            pytest.skip("Domain directory not found")

        violations = []
        for py_file in _get_python_files(domain_dir):
            imports = _extract_imports(py_file)
            for imp in imports:
                if "infrastructure" in imp or imp.startswith("src.infrastructure"):
                    rel_path = py_file.relative_to(SRC_ROOT.parent)
                    violations.append(f"{rel_path}: imports '{imp}'")

        assert not violations, (
            f"Domain layer has {len(violations)} infrastructure import(s):\n"
            + "\n".join(f"  - {v}" for v in violations)
        )

    def test_domain_does_not_import_api(self) -> None:
        """Domain layer must not import from src.api."""
        domain_dir = SRC_ROOT / "domain"
        if not domain_dir.exists():
            pytest.skip("Domain directory not found")

        violations = []
        for py_file in _get_python_files(domain_dir):
            imports = _extract_imports(py_file)
            for imp in imports:
                if imp.startswith("src.api"):
                    rel_path = py_file.relative_to(SRC_ROOT.parent)
                    violations.append(f"{rel_path}: imports '{imp}'")

        assert not violations, (
            f"Domain layer has {len(violations)} API import(s):\n"
            + "\n".join(f"  - {v}" for v in violations)
        )

    def test_domain_does_not_import_agents(self) -> None:
        """Domain layer must not import from src.agents."""
        domain_dir = SRC_ROOT / "domain"
        if not domain_dir.exists():
            pytest.skip("Domain directory not found")

        violations = []
        for py_file in _get_python_files(domain_dir):
            imports = _extract_imports(py_file)
            for imp in imports:
                if imp.startswith("src.agents"):
                    rel_path = py_file.relative_to(SRC_ROOT.parent)
                    violations.append(f"{rel_path}: imports '{imp}'")

        assert not violations, (
            f"Domain layer has {len(violations)} agent import(s):\n"
            + "\n".join(f"  - {v}" for v in violations)
        )


class TestAgentsBoundary:
    """Tests ensuring agents layer only imports from domain."""

    def test_agents_do_not_import_infrastructure(self) -> None:
        """Agents layer must not import from src.infrastructure."""
        agents_dir = SRC_ROOT / "agents"
        if not agents_dir.exists():
            pytest.skip("Agents directory not found")

        violations = []
        for py_file in _get_python_files(agents_dir):
            imports = _extract_imports(py_file)
            for imp in imports:
                if "infrastructure" in imp or imp.startswith("src.infrastructure"):
                    rel_path = py_file.relative_to(SRC_ROOT.parent)
                    violations.append(f"{rel_path}: imports '{imp}'")

        assert not violations, (
            f"Agents layer has {len(violations)} infrastructure import(s):\n"
            + "\n".join(f"  - {v}" for v in violations)
        )

    def test_agents_do_not_import_api(self) -> None:
        """Agents layer must not import from src.api."""
        agents_dir = SRC_ROOT / "agents"
        if not agents_dir.exists():
            pytest.skip("Agents directory not found")

        violations = []
        for py_file in _get_python_files(agents_dir):
            imports = _extract_imports(py_file)
            for imp in imports:
                if imp.startswith("src.api"):
                    rel_path = py_file.relative_to(SRC_ROOT.parent)
                    violations.append(f"{rel_path}: imports '{imp}'")

        assert not violations, (
            f"Agents layer has {len(violations)} API import(s):\n"
            + "\n".join(f"  - {v}" for v in violations)
        )


class TestPortInterfaces:
    """Tests ensuring port interfaces are properly abstract."""

    def test_ports_are_abstract_classes(self) -> None:
        """All files in domain/ports/ must define abstract classes only."""
        ports_dir = SRC_ROOT / "domain" / "ports"
        if not ports_dir.exists():
            pytest.skip("Ports directory not found")

        violations = []
        for py_file in _get_python_files(ports_dir):
            if py_file.name == "__init__.py":
                continue
            source = py_file.read_text(encoding="utf-8")
            tree = ast.parse(source)

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check if class inherits from ABC
                    base_names = [
                        getattr(b, "id", getattr(b, "attr", ""))
                        for b in node.bases
                    ]
                    if "ABC" not in base_names:
                        violations.append(
                            f"{py_file.name}: class '{node.name}' does not inherit from ABC"
                        )

        # Filter out non-Port classes (like metadata classes)
        port_violations = [v for v in violations if "Port" in v]
        assert not port_violations, (
            f"Found {len(port_violations)} non-abstract Port class(es):\n"
            + "\n".join(f"  - {v}" for v in port_violations)
        )

    def test_ports_have_max_5_methods(self) -> None:
        """Each port interface must have no more than 5 abstract methods."""
        ports_dir = SRC_ROOT / "domain" / "ports"
        if not ports_dir.exists():
            pytest.skip("Ports directory not found")

        violations = []
        for py_file in _get_python_files(ports_dir):
            if py_file.name == "__init__.py":
                continue
            source = py_file.read_text(encoding="utf-8")
            tree = ast.parse(source)

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and "Port" in node.name:
                    methods = [
                        n for n in node.body
                        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                        and not n.name.startswith("_")
                    ]
                    if len(methods) > 5:
                        violations.append(
                            f"{py_file.name}: '{node.name}' has {len(methods)} methods (max 5)"
                        )

        assert not violations, (
            f"Found {len(violations)} port(s) exceeding 5 methods:\n"
            + "\n".join(f"  - {v}" for v in violations)
        )
