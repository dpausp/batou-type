"""Integration tests for run_fix() on tmp_path projects.

Spec decision: test-strategy — run_fix() on tmp_path projects with real component files.
Real ty invocations, real file operations, real Diagnostic objects.
"""

from pathlib import Path

import click
import pytest

from batou_type.cli import run_fix
from batou_type.core import Checker


def _make_project(tmp_path: Path, name: str, source: str) -> Path:
    """Create a batou project with a single component."""
    project = tmp_path / name
    components = project / "components"
    components.mkdir(parents=True)
    (components / "comp.py").write_text(source)
    return project


# Component that triggers unresolved-attribute via self._ usage.
_SELF_DEREF_COMPONENT = """\
from batou.component import Component


class SubComp(Component):
    address: str = "localhost"


class MyComp(Component):
    address: str

    def configure(self):
        self += SubComp()
        addr = self._.address
"""


class TestRunFixNoFixable:
    """run_fix() with clean or non-fixable projects."""

    def test_clean_project_no_fixable_diagnostics(self, tmp_path: Path) -> None:
        """Clean component → no fixable diagnostics, exit 0."""
        project = _make_project(tmp_path, "clean", "def configure():\n    pass\n")
        with pytest.raises(click.exceptions.Exit) as exc_info:
            run_fix([project], fix=True, checker=[Checker.ty])
        assert exc_info.value.exit_code == 0


class TestRunFixSelfDeref:
    """run_fix() on projects with self._ deref patterns."""

    def test_diff_mode_produces_unified_diff(self, tmp_path: Path) -> None:
        """--diff mode produces unified diff output with walrus transformation."""
        project = _make_project(tmp_path, "deref", _SELF_DEREF_COMPONENT)
        with pytest.raises(click.exceptions.Exit) as exc_info:
            run_fix(
                [project],
                fix=True,
                diff=True,
                fix_only=True,
                checker=[Checker.ty],
            )
        assert exc_info.value.exit_code == 1

        # Verify file was NOT modified (diff mode is read-only)
        source = (project / "components" / "comp.py").read_text()
        assert "self._.address" in source
        assert "_ := SubComp()" not in source

    def test_fix_mode_writes_in_place(self, tmp_path: Path) -> None:
        """--fix mode writes transformed file in-place."""
        project = _make_project(tmp_path, "fixwrite", _SELF_DEREF_COMPONENT)
        with pytest.raises(click.exceptions.Exit) as exc_info:
            run_fix([project], fix=True, checker=[Checker.ty])
        assert exc_info.value.exit_code == 0

        source = (project / "components" / "comp.py").read_text()
        assert "_ := SubComp()" in source
        assert "self._.address" not in source
        assert "_.address" in source


class TestRunFixFlags:
    """Flag dispatch and exit code behavior."""

    def test_fix_only_suppresses_errors_exits_zero(self, tmp_path: Path) -> None:
        """--fix-only on a project with remaining errors exits 0 after fixing."""
        # Component with both a fixable self._ error AND an unfixable error
        source = """\
from batou.component import Component


class SubComp(Component):
    address: str = "localhost"


class MyComp(Component):
    address: str

    def configure(self):
        self += SubComp()
        addr = self._.address
        x: int = "wrong type"  # unfixable type error
"""
        project = _make_project(tmp_path, "fixonly", source)
        with pytest.raises(click.exceptions.Exit) as exc_info:
            run_fix(
                [project],
                fix=True,
                fix_only=True,
                checker=[Checker.ty],
            )
        # fix-only exits 0 as long as fixes applied successfully
        assert exc_info.value.exit_code == 0

        # Verify fixable part was fixed
        fixed = (project / "components" / "comp.py").read_text()
        assert "_ := SubComp()" in fixed
