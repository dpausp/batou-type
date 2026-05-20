"""Spec validation tests for batou_type modernization (Python 3.14+).

These tests define the modernization contract. All should now pass.

Changes covered:
  1. Keep ``from __future__ import annotations`` in core.py — required for
     Python 3.13 compatibility (TYPE_CHECKING guard with Diagnostic type).
  2. Add ``slots=True`` to all dataclass decorators in core.py.
  3. Use ``uv audit`` (built into uv) instead of pip-audit for vulnerability scanning.
"""

import ast
import subprocess

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


# --- 3. ``uv audit`` for vulnerability scanning ---


def test_uv_audit_available() -> None:
    """``uv audit`` must be available (built into uv, no separate package).

    uv audit replaces pip-audit. It is a built-in subcommand of uv,
    so no entry in dependency-groups.lint is needed.
    """
    result = subprocess.run(
        ["uv", "audit", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"uv audit not available: exit {result.returncode}, "
        f"stderr={result.stderr.strip()}"
    )


def test_uv_audit_runnable() -> None:
    """``uv audit`` must run successfully on the project dependencies.

    Known false positives are ignored via ``--ignore``. PYSEC-2022-42969
    is a withdrawn advisory that still appears in OSV — it affects the
    ``py`` package and has no fix version.
    """
    result = subprocess.run(
        ["uv", "audit", "--ignore", "PYSEC-2022-42969"],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    assert result.returncode == 0, (
        f"uv audit failed: exit {result.returncode}, "
        f"stdout={result.stdout.strip()}\n"
        f"stderr={result.stderr.strip()}"
    )
