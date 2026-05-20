"""Spec validation tests for batou_type modernization (Python 3.14+).

These tests define the modernization contract. All should now pass.

Changes covered:
  1. Keep ``from __future__ import annotations`` in core.py — required for
     Python 3.13 compatibility (TYPE_CHECKING guard with Diagnostic type).
  2. Add ``slots=True`` to all dataclass decorators in core.py.
  3. Add ``pip-audit`` to the ``[dependency-groups.lint]`` in pyproject.toml.
"""

import ast
import subprocess
import sys
import tomllib


from pathlib import Path

SRC = Path(__file__).resolve().parent.parent.parent / "src" / "batou_type"
ROOT = Path(__file__).resolve().parent.parent.parent


# --- 1. ``from __future__ import annotations`` policy ---


FUTURE_ANNOTATIONS_ALLOWLIST = {"core.py"}


def test_no_future_annotations() -> None:
    """No source file in src/batou_type/ (excluding vendor/) may contain
    ``from __future__ import annotations`` — except files in the allowlist.

    core.py is allowlisted because it uses ``if TYPE_CHECKING:`` to lazily
    import Diagnostic, and TypeCheckResult.errors references Diagnostic in
    its annotation. On Python 3.13 (without PEP 649), removing the
    ``__future__`` import causes NameError at class definition time.
    The import is a no-op on Python 3.14 but required for 3.13 compat.
    """
    for py_file in sorted(SRC.glob("*.py")):
        if "vendor" in py_file.parts:
            continue
        if py_file.name in FUTURE_ANNOTATIONS_ALLOWLIST:
            continue
        source = py_file.read_text()
        tree = ast.parse(source, filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "__future__":
                for alias in node.names:
                    assert alias.name != "annotations", (
                        f"{py_file.relative_to(ROOT)}: "
                        f"from __future__ import annotations found"
                    )


# --- 2. Add ``slots=True`` to dataclasses in core.py ---


def test_core_dataclasses_have_slots() -> None:
    """All dataclass decorators in core.py must include ``slots=True``.

    Phase 2 must:
      - Change ``@dataclass(frozen=True)`` on VenvInfo to
        ``@dataclass(frozen=True, slots=True)``.
      - Change bare ``@dataclass`` on TypeCheckResult to
        ``@dataclass(slots=True)``.
    Other modules (cli.py, fixer.py) already use slots=True.
    """
    source = (SRC / "core.py").read_text()
    tree = ast.parse(source, filename="core.py")

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for decorator in node.decorator_list:
            # Match ``@dataclass(...)`` — a Call with func=Name(id="dataclass")
            if not isinstance(decorator, ast.Call):
                continue
            func = decorator.func
            if not (isinstance(func, ast.Name) and func.id == "dataclass"):
                continue
            # Verify slots=True keyword is present
            has_slots = any(
                isinstance(kw.value, ast.Constant)
                and kw.value.value is True
                and isinstance(kw.arg, str)
                and kw.arg == "slots"
                for kw in decorator.keywords
            )
            assert has_slots, (
                f"@dataclass on {node.name} (line {node.lineno}) "
                f"must include slots=True"
            )


# --- 3. Add ``pip-audit`` to lint dependency group ---


def test_pip_audit_in_lint_dependencies() -> None:
    """pyproject.toml ``[dependency-groups.lint]`` must include ``pip-audit``.

    Phase 2 must: add ``"pip-audit"`` to the ``lint`` dependency group
    in pyproject.toml, alongside the existing ``pyupgrade`` and ``ruff``
    entries.
    """
    pyproject = ROOT / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text())
    lint_deps = data["dependency-groups"]["lint"]
    assert any("pip-audit" in dep for dep in lint_deps), (
        f"pip-audit not found in dependency-groups.lint: {lint_deps}"
    )


def test_pip_audit_runnable() -> None:
    """pip-audit must be installed and report its version.

    Phase 2 must: add pip-audit to lint dependencies so ``uv run pip-audit``
    works in the project environment.
    """
    result = subprocess.run(
        [sys.executable, "-m", "pip_audit", "--version"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"pip-audit not runnable: exit {result.returncode}, "
        f"stderr={result.stderr.strip()}"
    )
