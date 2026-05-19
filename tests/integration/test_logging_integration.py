"""Integration tests for logging events emitted by batou_type.

pytest-stogger AST-scans for log.has("event-id") in test files.
Uses pytest-structlog's `log` fixture for event capture and assertion.
"""

import click
from pathlib import Path
from typing import Any
from unittest.mock import patch


from batou_type.core import Checker, CheckerError


def _make_project(tmp_path: Path, *component_files: tuple[str, str]) -> Path:
    """Create a batou project with component files."""
    components = tmp_path / "components"
    components.mkdir(exist_ok=True)
    for name, content in component_files:
        (components / name).write_text(content)
    return tmp_path


def _run_check_capture(log: Any, paths: list[Path], **kwargs: Any) -> None:
    """Run run_check in-process with pytest-structlog capture."""
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
    events = {e["event"]: e for e in log.events}
    assert events["projects-found"]["project_count"] == 1


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
    assert log.has("components-failed-header")
    assert log.has("components-failed-project")
    assert log.has("components-failed-summary")


def test_checker_unavailable_logs_error(tmp_path, log) -> None:
    """Unavailable checker emits checker-unavailable event."""
    from batou_type.cli import run_check

    project = _make_project(tmp_path, ("comp.py", "def f(): pass\n"))
    with patch(
        "batou_type.cli.ensure_checker_available",
        autospec=True,
        side_effect=CheckerError("not found"),
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
    from batou_type.cli import setup

    (tmp_path / "components").mkdir()
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[tool.ty]\nstrict = true\n")
    try:
        setup(path=tmp_path)
    except (SystemExit, click.exceptions.Exit):
        pass
    assert log.has("setup-conflict")


def test_version_logs_events(log) -> None:
    """Version command emits version and stub-info events."""
    from batou_type.cli import version

    version()
    assert log.has("version")
    assert log.has("stub-info")


def test_stub_not_installed_logs_warning(log) -> None:
    """Missing stub emits stub-not-installed event."""
    from batou_type.cli import version, StubInfo

    with patch(
        "batou_type.cli._detect_all_stubs",
        return_value=[StubInfo(name="test-stubs", version=None, path=None)],
    ):
        version()
    assert log.has("stub-not-installed")


def test_setup_not_batou_project_logs_error(tmp_path, log) -> None:
    """Setup on non-batou directory emits not-a-batou-project event."""
    from batou_type.cli import setup

    try:
        setup(path=tmp_path)
    except (SystemExit, click.exceptions.Exit):
        pass
    assert log.has("not-a-batou-project")


def test_setup_unknown_checkers_logs_error(tmp_path, log) -> None:
    """Setup with unknown checkers emits unknown-checkers event."""
    from batou_type.cli import setup

    (tmp_path / "components").mkdir()
    try:
        setup(path=tmp_path, checkers="nonexistent")
    except (SystemExit, click.exceptions.Exit):
        pass
    assert log.has("unknown-checkers")


def test_setup_complete_logs_info(tmp_path, log) -> None:
    """Successful setup emits setup-complete event."""
    from batou_type.cli import setup

    (tmp_path / "components").mkdir()
    try:
        setup(path=tmp_path)
    except (SystemExit, click.exceptions.Exit):
        pass
    assert log.has("setup-complete")


def test_setup_dry_run_logs_info(tmp_path, log) -> None:
    """Dry run setup emits setup-dry-run event."""
    from batou_type.cli import setup

    (tmp_path / "components").mkdir()
    try:
        setup(path=tmp_path, dry_run=True)
    except (SystemExit, click.exceptions.Exit):
        pass
    assert log.has("setup-dry-run")
