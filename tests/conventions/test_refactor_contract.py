"""Spec validation tests for batou_type refactoring.

These tests define the contract that the refactoring must fulfill.
Currently xfail — Phase 2 makes them green.
"""

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent.parent / "src" / "batou_type"


# --- 1. cli.py exists and contains the CLI app ---


def test_cli_module_exists() -> None:
    """cli.py must exist as a module in batou_type package."""
    assert (SRC / "cli.py").is_file()


def test_cli_module_has_typer_app() -> None:
    """cli.py must define a Typer app instance."""
    # Don't import (would fail), parse AST
    tree = ast.parse((SRC / "cli.py").read_text())
    assignments = [node for node in ast.walk(tree) if isinstance(node, ast.Assign)]
    # Must have an `app` assignment that is a Call (typer.Typer())
    app_assigns = [
        a
        for a in assignments
        if any(t.id == "app" for t in a.targets if isinstance(t, ast.Name))
    ]
    assert len(app_assigns) >= 1


# --- 2. __init__.py is lean ---


def test_init_no_typer_import() -> None:
    """__init__.py must NOT import typer."""
    source = (SRC / "__init__.py").read_text()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert "typer" not in alias.name
        if isinstance(node, ast.ImportFrom):
            assert node.module is None or "typer" not in node.module


def test_init_no_rich_import() -> None:
    """__init__.py must NOT import rich."""
    source = (SRC / "__init__.py").read_text()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert "rich" not in alias.name
        if isinstance(node, ast.ImportFrom):
            assert node.module is None or "rich" not in node.module


def test_init_exports_version() -> None:
    """__init__.py must define __version__."""
    source = (SRC / "__init__.py").read_text()
    tree = ast.parse(source)
    names = [
        node.targets[0].id
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
    ]
    assert "__version__" in names


# --- 3. __main__.py imports from cli ---


def test_main_imports_from_cli() -> None:
    """__main__.py must import app from batou_type.cli, not batou_type."""
    source = (SRC / "__main__.py").read_text()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert node.module == "batou_type.cli"
            assert any(alias.name == "app" for alias in node.names)


# --- 4. Entry point in pyproject.toml ---


def test_pyproject_entry_point_uses_cli() -> None:
    """pyproject.toml must reference batou_type.cli:app."""
    pyproject = Path(__file__).resolve().parent.parent.parent / "pyproject.toml"
    content = pyproject.read_text()
    assert "batou_type.cli:app" in content


# --- 5. core.py: top-level imports ---


def test_core_no_lazy_json_import() -> None:
    """core.py must import json at top level, not lazily in a function."""
    source = (SRC / "core.py").read_text()
    # Check that `import json` is NOT inside any function
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for child in ast.walk(node):
                if isinstance(child, ast.Import):
                    for alias in child.names:
                        assert alias.name != "json", (
                            f"json imported lazily in function '{node.name}'"
                        )


def test_core_no_lazy_io_import() -> None:
    """core.py must import io at top level, not lazily in a function."""
    source = (SRC / "core.py").read_text()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for child in ast.walk(node):
                if isinstance(child, ast.Import):
                    for alias in child.names:
                        assert alias.name != "io", (
                            f"io imported lazily in function '{node.name}'"
                        )


# --- 6. pytest_plugin.py: dead code removed ---


def test_plugin_no_batou_ty_error() -> None:
    """BatouTyError class must be removed (dead code)."""
    source = (SRC / "pytest_plugin.py").read_text()
    tree = ast.parse(source)
    class_names = [
        node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)
    ]
    assert "BatouTyError" not in class_names


# --- 7. No bare except Exception in __init__.py ---


def test_init_no_bare_except_exception() -> None:
    """__init__.py must not contain bare 'except Exception' after refactoring."""
    source = (SRC / "__init__.py").read_text()
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            assert node.type is None or (
                isinstance(node.type, ast.Name) and node.type.id != "Exception"
            ), "Bare 'except Exception' found in __init__.py"


# --- 8. Functional: imports still work ---


def test_core_imports_still_work() -> None:
    """Core module must still be importable with same public API."""
    from batou_type.core import (  # noqa: F401
        Checker,
        TypeCheckResult,  # noqa: F401
        check_all,  # noqa: F401
        check_file,  # noqa: F401
        find_components,  # noqa: F401
    )

    assert Checker.ty.value == "ty"


def test_cli_imports_work() -> None:
    """CLI module must be importable."""
    from batou_type.cli import app

    assert app is not None


def test_init_reexports_core() -> None:
    """__init__.py must re-export core types."""
    import batou_type

    assert hasattr(batou_type, "Checker")
    assert hasattr(batou_type, "TypeCheckResult")
    assert hasattr(batou_type, "__version__")
