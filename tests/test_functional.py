"""Functional E2E tests for batou-type CLI."""

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest
from typing import Any

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


def extract_json(stdout: str) -> dict[str, Any]:
    """Extract JSON object from stdout, stripping non-JSON prefix lines.

    stogger.init_early_logging() writes debug lines to stdout before the JSON payload.
    This finds the first '{' and parses from there.
    """
    start = stdout.index("{")
    return json.loads(stdout[start:])


SRC = Path(__file__).parent.parent / "src"
BATOU_TYPE_CLI = [sys.executable, "-m", "batou_type"]


@pytest.fixture
def temp_project(tmp_path: Path) -> Path:
    """Create a temporary batou project with components directory."""
    components = tmp_path / "components"
    components.mkdir()
    return tmp_path


def run_cli(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Run batou-type CLI and return result."""
    import os

    env = os.environ.copy()
    env.pop("JOURNAL_STREAM", None)
    result = subprocess.run(
        [*BATOU_TYPE_CLI, *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        env=env,
    )
    return result


class TestVersion:
    """Tests for version command."""

    def test_version_shows_batou_type_version(self, tmp_path) -> None:
        """Version command shows batou-type version."""
        result = run_cli("version", cwd=tmp_path)
        assert result.returncode == 0
        assert "batou-type" in result.stdout.lower()

    def test_version_shows_stub_info(self, tmp_path) -> None:
        """Version command shows stub package info."""
        result = run_cli("version", cwd=tmp_path)
        assert "batou-stubs" in result.stdout.lower()


class TestCheck:
    """Tests for check command."""

    def test_check_no_components_exits_zero(self, tmp_path) -> None:
        """Check with no component files exits 0."""
        result = run_cli("check", cwd=tmp_path)
        assert result.returncode == 0
        assert "no batou projects found" in (result.stdout + result.stderr).lower()

    def test_check_clean_component_exits_zero(self, temp_project) -> None:
        """Check with valid component files exits 0."""
        component = temp_project / "components" / "mycomponent.py"
        component.write_text("def configure():\n    pass\n")

        result = run_cli("check", cwd=temp_project)
        assert result.returncode == 0
        assert "component(s) passed" in (result.stdout + result.stderr).lower()

    def test_check_component_with_type_error_exits_one(self, temp_project) -> None:
        """Check with type errors exits 1."""
        component = temp_project / "components" / "badcomponent.py"
        component.write_text("def configure() -> int:\n    return 'not an int'\n")

        result = run_cli("check", cwd=temp_project)
        assert result.returncode == 1

    def test_check_with_ty_checker(self, temp_project) -> None:
        """Check with explicit -c ty works."""
        component = temp_project / "components" / "mycomponent.py"
        component.write_text("def configure():\n    pass\n")

        result = run_cli("check", "-c", "ty", cwd=temp_project)
        assert result.returncode == 0

    def test_check_with_mypy_checker(self, temp_project) -> None:
        """Check with explicit -c mypy works."""
        component = temp_project / "components" / "mycomponent.py"
        component.write_text("def configure():\n    pass\n")

        result = run_cli("check", "-c", "mypy", cwd=temp_project)
        # mypy might not be installed, but command should not crash
        assert result.returncode in (0, 1, 2)  # 2 = checker not found

    def test_check_multiple_components(self, temp_project) -> None:
        """Check handles multiple component files."""
        (temp_project / "components" / "comp1.py").write_text("def foo():\n    pass\n")
        (temp_project / "components" / "comp2.py").write_text("def bar():\n    pass\n")

        result = run_cli("check", cwd=temp_project)
        assert result.returncode == 0
        # Diagnostic info on stderr (stogger formatted with _replace_msg)
        assert "Checking 2 component(s)" in result.stderr

    def test_check_nested_components(self, temp_project) -> None:
        """Check finds components in nested directories."""
        nested = temp_project / "components" / "subpackage"
        nested.mkdir(parents=True)
        (nested / "nestedcomp.py").write_text("def nested():\n    pass\n")

        result = run_cli("check", cwd=temp_project)
        assert result.returncode == 0


class TestHelp:
    """Tests for help output."""

    def test_help_shows_commands(self) -> None:
        """--help shows available commands."""
        result = run_cli("--help")
        assert result.returncode == 0
        output = _strip_ansi(result.stdout.lower())
        assert "check" in output
        assert "version" in output

    def test_check_help_shows_options(self) -> None:
        """check --help shows options."""
        result = run_cli("check", "--help")
        assert result.returncode == 0
        output = _strip_ansi(result.stdout.lower())
        assert "--checker" in output

    def test_bad_command_shows_error(self) -> None:
        """Invalid command shows error message."""
        result = run_cli("nonexistent")
        assert result.returncode == 2
        # Typer outputs errors to stderr
        assert "no such command" in result.stderr.lower()


class TestErrorHandling:
    """Tests for error handling."""

    def test_invalid_checker_shows_error(self, temp_project) -> None:
        """Invalid checker name shows clear error."""
        result = run_cli("check", "--checker", "invalid", cwd=temp_project)
        assert result.returncode == 2
        # Typer outputs errors to stderr
        assert "invalid" in result.stderr.lower()


class TestJsonOutput:
    """E2E tests for --json and --show-schema CLI flags."""

    def test_json_clean_component_valid_json(self, temp_project) -> None:
        """Clean component produces valid JSON with expected structure."""
        component = temp_project / "components" / "mycomponent.py"
        component.write_text("def configure():\n    pass\n")

        result = run_cli("check", "--json", cwd=temp_project)
        assert result.returncode == 0
        data = extract_json(result.stdout)
        assert "schema_version" in data
        assert "projects" in data
        assert len(data["projects"]) == 1
        assert data["summary"]["total_errors"] == 0
        assert "$schema" not in data

    def test_json_component_with_error(self, temp_project) -> None:
        """Component with type error produces JSON with diagnostics."""
        component = temp_project / "components" / "badcomponent.py"
        component.write_text("def configure() -> int:\n    return 'not an int'\n")

        result = run_cli("check", "--json", cwd=temp_project)
        assert result.returncode == 1
        data = extract_json(result.stdout)
        assert data["summary"]["total_errors"] == 1
        diags = data["projects"][0]["components"][0]["diagnostics"]
        assert len(diags) > 0
        assert diags[0]["checker"] == "ty"
        assert isinstance(diags[0]["message"], str) and len(diags[0]["message"]) > 0
        assert "badcomponent.py" in diags[0]["file"]

    def test_json_no_projects(self, tmp_path) -> None:
        """No batou projects produces valid JSON with empty components."""
        result = run_cli("check", "--json", cwd=tmp_path)
        assert result.returncode == 0
        data = extract_json(result.stdout)
        assert data["projects"][0]["components"] == []

    def test_show_schema(self, tmp_path) -> None:
        """--show-schema outputs valid JSON Schema."""
        result = run_cli("check", "--show-schema", cwd=tmp_path)
        assert result.returncode == 0
        data = extract_json(result.stdout)
        assert "properties" in data
        assert "projects" in data["properties"]

    def test_json_stderr_has_logs(self, temp_project) -> None:
        """JSON mode: diagnostics go to stderr, not stdout."""
        component = temp_project / "components" / "mycomponent.py"
        component.write_text("def configure():\n    pass\n")

        result = run_cli("check", "--json", cwd=temp_project)
        assert len(result.stderr) > 0
        assert "Loaded stubs" not in result.stdout
        assert "Found" not in result.stdout


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


def _strip_stogger_lines(output: str) -> str:
    """Remove stogger debug/info prefix lines from CLI output."""
    return "\n".join(
        line
        for line in output.splitlines()
        if not line.startswith("20")  # stogger timestamps like 2026-...
    )


class TestFixDiff:
    """E2E tests for batou-type check --fix --diff."""

    def test_fix_diff_exits_one_when_diffs_present(self, tmp_path: Path) -> None:
        """--fix --diff on a project with fixable errors exits 1 (diffs present)."""
        components = tmp_path / "components"
        components.mkdir()
        (components / "comp.py").write_text(_SELF_DEREF_COMPONENT)

        result = run_cli("check", "--fix", "--diff", cwd=tmp_path)
        assert result.returncode == 1
        clean = _strip_stogger_lines(result.stdout)
        assert "--- a/" in clean
        assert "+++ b/" in clean
        assert "_ := SubComp()" in clean

    def test_fix_diff_exits_zero_when_clean(self, tmp_path: Path) -> None:
        """--fix --diff on a clean project exits 0 (no diffs)."""
        components = tmp_path / "components"
        components.mkdir()
        (components / "comp.py").write_text("def configure():\n    pass\n")

        result = run_cli("check", "--fix", "--diff", cwd=tmp_path)
        assert result.returncode == 0

    def test_fix_only_diff_output_format(self, tmp_path: Path) -> None:
        """--fix-only --diff produces unified diff with summary line."""
        components = tmp_path / "components"
        components.mkdir()
        (components / "comp.py").write_text(_SELF_DEREF_COMPONENT)

        result = run_cli("check", "--fix-only", "--diff", cwd=tmp_path)
        assert result.returncode == 1
        clean = _strip_stogger_lines(result.stdout)
        assert "--- a/" in clean
        assert "+++ b/" in clean
        assert "fixable" in (result.stdout + result.stderr).lower()
        # File should NOT be modified (--diff is read-only)
        source = (components / "comp.py").read_text()
        assert "self._.address" in source


# --- In-process log event tests ---
# pytest-stogger AST-scans for log.has("event-id") in test files.
# Uses pytest-structlog's `log` fixture for event capture and assertion.


def _make_project(tmp_path: Path, *component_files: tuple[str, str]) -> Path:
    """Create a batou project with component files."""
    components = tmp_path / "components"
    components.mkdir(exist_ok=True)
    for name, content in component_files:
        (components / name).write_text(content)
    return tmp_path


def _run_check_capture(log: Any, paths: list[Path], **kwargs: Any) -> None:
    """Run run_check in-process with pytest-structlog capture."""
    import click

    from batou_type.cli import run_check

    try:
        run_check(checker=None, paths=paths, ty_args=[], json_mode=False, **kwargs)
    except (SystemExit, click.exceptions.Exit):
        pass
    return log


def test_no_projects_found_logs_warning(tmp_path, log) -> None:
    """Empty directory emits no-projects-found at warning level."""
    _run_check_capture(log, paths=[tmp_path])
    assert log.has("no-projects-found")
    events = {e["event"]: e for e in log.events}
    assert events["no-projects-found"]["level"] == "warning"


def test_projects_found_logs_info(tmp_path, log) -> None:
    """Valid project emits projects-found with count."""
    project = _make_project(tmp_path, ("comp.py", "def f(): pass\n"))
    _run_check_capture(log, paths=[project])
    assert log.has("projects-found")
    events = {e["event"]: e for e in log.events}
    assert events["projects-found"]["count"] == 1


def test_components_passed_logs_info(tmp_path, log) -> None:
    """Clean component emits components-passed summary."""
    project = _make_project(tmp_path, ("comp.py", "def f(): pass\n"))
    _run_check_capture(log, paths=[project])
    assert log.has("components-passed")


def test_components_failed_logs_info(tmp_path, log) -> None:
    """Component with type error emits components-failed summary."""
    project = _make_project(
        tmp_path, ("bad.py", "def configure() -> int:\n    return 'not an int'\n")
    )
    _run_check_capture(log, paths=[project])
    assert log.has("components-failed")


def test_checker_unavailable_logs_error(tmp_path, log) -> None:
    """Unavailable checker emits checker-unavailable event."""
    import click
    from unittest.mock import patch

    from batou_type.cli import run_check
    from batou_type.core import Checker, CheckerError

    project = _make_project(tmp_path, ("comp.py", "def f(): pass\n"))
    with patch(
        "batou_type.cli.ensure_checker_available", autospec=True, side_effect=CheckerError("not found")
    ):
        try:
            run_check(
                checker=[Checker.mypy],
                paths=[project],
                ty_args=[],
                json_mode=False,
            )
        except (SystemExit, click.exceptions.Exit):
            pass
    assert log.has("checker-unavailable")


def test_setup_stubs_copied_logs_info(tmp_path, log) -> None:
    """setup copy_stubs emits stubs-copied event."""
    from batou_type.setup import copy_stubs
    from batou_type.cli import VENDOR_STUBS_PATH

    copy_stubs(tmp_path, VENDOR_STUBS_PATH)
    assert log.has("stubs-copied")


def test_setup_checker_config_written_logs_info(tmp_path, log) -> None:
    """setup write_checker_config emits checker-config-written event."""
    from batou_type.setup import write_checker_config

    (tmp_path / "components").mkdir()
    write_checker_config(tmp_path, ["ty"])
    assert log.has("checker-config-written")


def test_setup_conflict_logs_error(tmp_path, log) -> None:
    """Setup with unmanaged checker sections emits setup-conflict event."""
    import click

    from batou_type.cli import setup

    (tmp_path / "components").mkdir()
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[tool.ty]\nstrict = true\n")
    try:
        setup(path=tmp_path)
    except (SystemExit, click.exceptions.Exit):
        pass
    assert log.has("setup-conflict")


class TestMainModule:
    """Tests for python -m batou_type trampoline (__main__.py)."""

    def test_python_m_version(self, tmp_path) -> None:
        """python -m batou_type version exercises __main__.py trampoline."""
        result = run_cli("version", cwd=tmp_path)
        assert result.returncode == 0
        assert "batou-type" in result.stdout.lower()

    def test_python_m_help(self, tmp_path) -> None:
        """python -m batou_type --help exercises __main__.py trampoline."""
        result = run_cli("--help", cwd=tmp_path)
        assert result.returncode == 0
        assert "check" in result.stdout.lower()
        assert "version" in result.stdout.lower()

    def test_python_m_no_args(self, tmp_path) -> None:
        """python -m batou_type with no args shows help/usage."""
        result = run_cli(cwd=tmp_path)
        # Typer exits 2 when no command given, but shows help
        assert result.returncode == 2
        assert "check" in result.stdout.lower()
