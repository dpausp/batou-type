"""In-process logging event tests for stogger convention coverage."""

import os

import click.exceptions
from structlog.testing import capture_logs

from batou_type.cli import run_check


def _env_without_journal():
    """Environment without JOURNAL_STREAM (prevents stogger journal mode)."""
    env = os.environ.copy()
    env.pop("JOURNAL_STREAM", None)
    return env


def _make_project(tmp_path, *component_files):
    """Create a batou project with component files."""
    components = tmp_path / "components"
    components.mkdir(exist_ok=True)
    for name, content in component_files:
        (components / name).write_text(content)
    return tmp_path


def _run_and_capture(checker=None, paths=None, json_mode=False):
    """Run run_check with captured log events."""
    with capture_logs() as cap:
        try:
            run_check(
                checker=checker,
                paths=paths or [],
                ty_args=[],
                json_mode=json_mode,
            )
        except (SystemExit, click.exceptions.Exit):
            pass
    return cap


def _event_ids(captured):
    """Extract event IDs from captured logs."""
    return [e["event"] for e in captured]


class TestNoProjectsFound:
    """no-projects-found event when no batou projects exist."""

    def test_emits_no_projects_found(self, tmp_path):
        """Emits no-projects-found warning for empty directory."""
        captured = _run_and_capture(paths=[tmp_path])
        assert "no-projects-found" in _event_ids(captured)

    def test_no_projects_found_is_warning(self, tmp_path):
        """no-projects-found is emitted at warning level."""
        captured = _run_and_capture(paths=[tmp_path])
        events = {e["event"]: e for e in captured}
        assert events["no-projects-found"]["log_level"] == "warning"

    def test_no_projects_found_has_paths_context(self, tmp_path):
        """no-projects-found includes paths kwarg."""
        captured = _run_and_capture(paths=[tmp_path])
        events = {e["event"]: e for e in captured}
        assert "paths" in events["no-projects-found"]


class TestProjectDiscovery:
    """projects-found and project events."""

    def test_emits_projects_found(self, tmp_path):
        """Emits projects-found when batou projects discovered."""
        project = _make_project(tmp_path, ("comp.py", "def f(): pass\n"))
        captured = _run_and_capture(paths=[project])
        assert "projects-found" in _event_ids(captured)

    def test_projects_found_has_count(self, tmp_path):
        """projects-found includes count kwarg."""
        project = _make_project(tmp_path, ("comp.py", "def f(): pass\n"))
        captured = _run_and_capture(paths=[project])
        events = {e["event"]: e for e in captured}
        assert events["projects-found"]["count"] == 1

    def test_emits_project_per_project(self, tmp_path):
        """Emits one project event per discovered project."""
        project = _make_project(tmp_path, ("comp.py", "def f(): pass\n"))
        captured = _run_and_capture(paths=[project])
        assert "project" in _event_ids(captured)


class TestCheckingEvents:
    """checking-components and venv events."""

    def test_emits_checking_components(self, tmp_path):
        """Emits checking-components before running checks."""
        project = _make_project(tmp_path, ("comp.py", "def f(): pass\n"))
        captured = _run_and_capture(paths=[project])
        assert "checking-components" in _event_ids(captured)

    def test_checking_components_has_count(self, tmp_path):
        """checking-components includes component count."""
        project = _make_project(
            tmp_path,
            ("comp1.py", "def f(): pass\n"),
            ("comp2.py", "def g(): pass\n"),
        )
        captured = _run_and_capture(paths=[project])
        events = {e["event"]: e for e in captured}
        assert events["checking-components"]["count"] == 2

    def test_project_context_via_bind(self, tmp_path):
        """checking-components has project from log.bind()."""
        project = _make_project(tmp_path, ("comp.py", "def f(): pass\n"))
        captured = _run_and_capture(paths=[project])
        events = {e["event"]: e for e in captured}
        checking = events["checking-components"]
        assert "project" in checking


class TestComponentResultEvents:
    """component-result events per checked component."""

    def test_emits_component_result(self, tmp_path):
        """Emits component-result for each component."""
        project = _make_project(tmp_path, ("comp.py", "def f(): pass\n"))
        captured = _run_and_capture(paths=[project])
        assert "component-result" in _event_ids(captured)

    def test_component_result_has_name_and_status(self, tmp_path):
        """component-result includes component name and passed flag."""
        project = _make_project(tmp_path, ("mycomp.py", "def f(): pass\n"))
        captured = _run_and_capture(paths=[project])
        results = [e for e in captured if e["event"] == "component-result"]
        assert results[0]["component"] == "mycomp"
        assert "passed" in results[0]
        assert "status" in results[0]


class TestSummaryEvents:
    """components-passed and components-failed summary events."""

    def test_emits_components_passed(self, tmp_path):
        """Emits components-passed when all components pass."""
        project = _make_project(tmp_path, ("comp.py", "def f(): pass\n"))
        captured = _run_and_capture(paths=[project])
        assert "components-passed" in _event_ids(captured)

    def test_components_passed_has_count(self, tmp_path):
        """components-passed includes total count."""
        project = _make_project(
            tmp_path,
            ("comp1.py", "def f(): pass\n"),
            ("comp2.py", "def g(): pass\n"),
        )
        captured = _run_and_capture(paths=[project])
        events = {e["event"]: e for e in captured}
        assert events["components-passed"]["count"] == 2


class TestDebugEvents:
    """Debug-level internal events."""

    def test_emits_python_info(self, tmp_path):
        """Emits python-info with executable path."""
        project = _make_project(tmp_path, ("comp.py", "def f(): pass\n"))
        captured = _run_and_capture(paths=[project])
        assert "python-info" in _event_ids(captured)

    def test_emits_stub_events(self, tmp_path):
        """Emits stub-info or stub-not-installed for each stub."""
        project = _make_project(tmp_path, ("comp.py", "def f(): pass\n"))
        captured = _run_and_capture(paths=[project])
        event_ids = _event_ids(captured)
        stub_events = [e for e in event_ids if e.startswith("stub-")]
        assert len(stub_events) >= 1

    def test_venv_events_are_debug_level(self, tmp_path):
        """project-venv and no-venv are debug level."""
        project = _make_project(tmp_path, ("comp.py", "def f(): pass\n"))
        captured = _run_and_capture(paths=[project])
        venv_events = [e for e in captured if e["event"] in ("project-venv", "no-venv")]
        for evt in venv_events:
            assert evt["log_level"] == "debug"
