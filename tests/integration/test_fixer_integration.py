"""Integration tests for run_fix() on tmp_path projects.

Spec decision: test-strategy — run_fix() on tmp_path projects with real component files.
Real ty invocations, real file operations, real Diagnostic objects.
"""
import re
from pathlib import Path

import click
import pytest
from typer.testing import CliRunner
from unittest.mock import patch

from batou_type.cli import app, run_fix
from batou_type.core import Checker


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


def _make_project(tmp_path: Path, name: str, source: str) -> Path:
    """Create a batou project with a single component."""
    project = tmp_path / name
    components = project / "components"
    components.mkdir(parents=True)
    (components / "comp.py").write_text(source)
    return project


# --- run_fix() with clean or non-fixable projects ---


def test_clean_project_no_fixable_diagnostics(tmp_path: Path, log) -> None:
    """Clean component → no fixable diagnostics, exit 0."""
    project = _make_project(tmp_path, "clean", "def configure():\n    pass\n")
    with pytest.raises(click.exceptions.Exit) as exc_info:
        run_fix([project], fix=True, checker=[Checker.ty])
    assert exc_info.value.exit_code == 0
    assert log.has("fix-no-fixable-found")


# --- run_fix() on projects with self._ deref patterns ---


def test_diff_mode_produces_unified_diff(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], log
) -> None:
    """--diff mode produces unified diff output with walrus transformation."""
    # SPEC: diff-generation — verify unified diff format and content
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

    # SPEC: diff-generation — assert unified diff format headers and content
    captured = capsys.readouterr()
    diff_output = re.sub(r"\x1b\[[0-9;]*m", "", captured.out)
    # Unified diff headers with a/ and b/ prefixes
    assert "--- a/" in diff_output, f"Missing --- header in diff: {diff_output!r}"
    assert "+++ b/" in diff_output, f"Missing +++ header in diff: {diff_output!r}"
    # At least one removed line and one added line
    removed = [
        line
        for line in diff_output.splitlines()
        if line.startswith("-") and not line.startswith("---")
    ]
    added = [
        line
        for line in diff_output.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    ]
    assert len(removed) >= 1, f"No removed lines in diff: {diff_output!r}"
    assert len(added) >= 1, f"No added lines in diff: {diff_output!r}"
    # File path appears in diff headers
    assert "comp.py" in diff_output, f"File path missing from diff: {diff_output!r}"
    assert log.has("fix-diff-summary")


def test_fix_mode_writes_in_place(tmp_path: Path, log) -> None:
    """--fix mode writes transformed file in-place."""
    project = _make_project(tmp_path, "fixwrite", _SELF_DEREF_COMPONENT)
    with pytest.raises(click.exceptions.Exit) as exc_info:
        run_fix([project], fix=True, checker=[Checker.ty])
    assert exc_info.value.exit_code == 0

    source = (project / "components" / "comp.py").read_text()
    assert "_ := SubComp()" in source
    assert "self._.address" not in source
    assert "_.address" in source
    assert log.has("fix-applied-summary")


# --- Flag dispatch and exit code behavior ---


def test_fix_only_suppresses_errors_exits_zero(tmp_path: Path) -> None:
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


# --- run_fix() with --virtual flag ---


def test_virtual_mode_applies_fix_after_verification(tmp_path: Path) -> None:
    """Virtual mode verifies in tempdir, then applies fix to original."""
    # SPEC: virtual-mode-impl — successful verification then fix
    project = _make_project(tmp_path, "virtual_ok", _SELF_DEREF_COMPONENT)
    with pytest.raises(click.exceptions.Exit) as exc_info:
        run_fix(
            [project],
            fix=True,
            virtual=True,
            checker=[Checker.ty],
        )
    assert exc_info.value.exit_code == 0

    # Original file IS modified after successful virtual verification
    source = (project / "components" / "comp.py").read_text()
    assert "_ := SubComp()" in source
    assert "self._.address" not in source


def test_virtual_mode_rejects_when_errors_not_reduced(tmp_path: Path, log) -> None:
    """Virtual mode exits 1 when fixes don't reduce error count."""
    # SPEC: virtual-mode-impl — rejection when errors not reduced
    # Component with fixable self._ AND unfixable type error — after fix,
    # file still has errors so virtual verification rejects the change.
    source = """\
from batou.component import Component


class SubComp(Component):
    address: str = "localhost"


class MyComp(Component):
    address: str

    def configure(self):
        self += SubComp()
        addr = self._.address
        x: int = "wrong type"  # unfixable
"""
    project = _make_project(tmp_path, "virtual_fail", source)
    original = (project / "components" / "comp.py").read_text()

    with pytest.raises(click.exceptions.Exit) as exc_info:
        run_fix(
            [project],
            fix=True,
            virtual=True,
            checker=[Checker.ty],
        )
    assert exc_info.value.exit_code == 1

    # Original file NOT modified — virtual check rejected the fix
    current = (project / "components" / "comp.py").read_text()
    assert current == original
    assert "self._.address" in current
    assert log.has("fix-no-improvement")


def test_virtual_mode_clean_project_exits_zero(tmp_path: Path) -> None:
    """Virtual mode on a clean project exits 0 (no fixable diagnostics)."""
    # SPEC: virtual-mode-impl — clean project with no fixable diagnostics
    project = _make_project(
        tmp_path, "virtual_clean", "def configure():\n    pass\n"
    )
    with pytest.raises(click.exceptions.Exit) as exc_info:
        run_fix(
            [project],
            fix=True,
            virtual=True,
            checker=[Checker.ty],
        )
    assert exc_info.value.exit_code == 0

    # File unchanged
    source = (project / "components" / "comp.py").read_text()
    assert source == "def configure():\n    pass\n"


# --- Flag dispatch runtime implication chain ---


def test_diff_implies_fix_only_and_fix(tmp_path: Path) -> None:
    """--diff at CLI level causes run_fix to receive fix_only=True and fix=True."""
    project = _make_project(tmp_path, "flagdiff", _SELF_DEREF_COMPONENT)

    runner = CliRunner()
    with patch("batou_type.cli.run_fix", autospec=True) as mock_run_fix:
        mock_run_fix.return_value = None
        runner.invoke(app, ["check", "--diff", str(project)])

    mock_run_fix.assert_called_once()
    kwargs = mock_run_fix.call_args.kwargs
    # SPEC: flag-dispatch — diff implies fix_only and fix
    assert kwargs["diff"] is True
    assert kwargs["fix_only"] is True
    assert kwargs["fix"] is True


def test_fix_only_implies_fix(tmp_path: Path) -> None:
    """--fix-only at CLI level causes run_fix to receive fix=True."""
    project = _make_project(tmp_path, "flagfixonly", _SELF_DEREF_COMPONENT)

    runner = CliRunner()
    with patch("batou_type.cli.run_fix", autospec=True) as mock_run_fix:
        mock_run_fix.return_value = None
        runner.invoke(app, ["check", "--fix-only", str(project)])

    mock_run_fix.assert_called_once()
    kwargs = mock_run_fix.call_args.kwargs
    # SPEC: flag-dispatch — fix_only implies fix
    assert kwargs["fix_only"] is True
    assert kwargs["fix"] is True
    # diff should NOT be set when only --fix-only is passed
    assert kwargs["diff"] is False


# SPEC: fix-pipeline — verify check_all called with json_mode=True
def test_run_fix_calls_check_all_with_json_mode(tmp_path: Path) -> None:
    """run_fix() must call check_all with json_mode=True to get Diagnostic objects."""
    from batou_type.core import TypeCheckResult
    from batou_type.output import Diagnostic

    project = _make_project(tmp_path, "jsonmode", _SELF_DEREF_COMPONENT)

    diag = Diagnostic(
        file="components/comp.py",
        line=10,
        message="Cannot resolve attribute",
        code="unresolved-attribute",
        checker="ty",
    )
    mock_result = TypeCheckResult(
        path="components/comp.py",
        has_errors=True,
        output="",
        errors=[diag],
    )

    with patch(
        "batou_type.cli.check_all", autospec=True, return_value=[mock_result]
    ) as mock_check_all:
        with pytest.raises(click.exceptions.Exit):
            run_fix([project], fix=True, checker=[Checker.ty])

        mock_check_all.assert_called_once()
        assert mock_check_all.call_args.kwargs["json_mode"] is True
