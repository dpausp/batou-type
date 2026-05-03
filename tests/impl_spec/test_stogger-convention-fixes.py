"""Spec contract tests for stogger-convention-fixes (9 decisions).

Phase 1 contract tests validating that the code structure, function signatures,
and logging event definitions match the spec contract.
"""

import ast
import inspect

from structlog.testing import capture_logs

from batou_type.cli import run_check


# --- Helpers ---


def _make_project(tmp_path, *component_files):
    """Create a batou project with component files."""
    components = tmp_path / "components"
    components.mkdir(exist_ok=True)
    for name, content in component_files:
        (components / name).write_text(content)
    return tmp_path


def _run_and_capture(checker=None, paths=None, json_mode=False):
    """Run run_check with captured log events."""
    import click.exceptions

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


def _events_by_id(captured, event_id):
    """Get all events matching an event ID."""
    return [e for e in captured if e["event"] == event_id]


# --- Decision 1: function-visibility ---


class TestFunctionVisibility:
    """run_check must be a public function (no underscore prefix).

    Spec decision: function-visibility
    """

    def test_run_check_is_public(self):
        """run_check is exported as a public function (no _ prefix)."""
        import batou_type.cli as cli_mod

        assert hasattr(cli_mod, "run_check"), (
            "run_check must be importable from batou_type.cli"
        )
        assert not cli_mod.run_check.__name__.startswith("_"), (
            "run_check must not have underscore prefix"
        )

    def test_run_check_is_callable(self):
        """run_check is a callable function."""
        assert callable(run_check)

    def test_no_private_run_check_exists(self):
        """_run_check must NOT exist as a function."""
        import batou_type.cli as cli_mod

        assert not hasattr(cli_mod, "_run_check"), (
            "_run_check must not exist — renamed to run_check"
        )


# --- Decision 2: branch-dedup ---


class TestBranchDedup:
    """run_check must have a single project loop (no duplicated branches).

    Spec decision: branch-dedup
    """

    def test_single_project_loop(self):
        """run_check has exactly one 'for project in projects' loop."""
        source = inspect.getsource(run_check)
        tree = ast.parse(source)

        loop_count = 0
        for node in ast.walk(tree):
            if isinstance(node, ast.For):
                try:
                    target_name = node.target.id  # ty: ignore[unresolved-attribute]
                    iter_name = ast.dump(node.iter)
                    if "projects" in iter_name and target_name == "project":
                        loop_count += 1
                except AttributeError:
                    pass

        assert loop_count == 1, (
            f"Expected exactly 1 'for project in projects' loop, found {loop_count}"
        )

    def test_venv_detection_in_single_location(self):
        """Venv detection (find_project_venv) called once per iteration, not duplicated."""
        source = inspect.getsource(run_check)
        count = source.count("find_project_venv")
        assert count == 1, (
            f"find_project_venv should be called once, found {count} occurrences"
        )

    def test_check_all_called_once_in_loop(self):
        """check_all() called once per project iteration, not in duplicated branches."""
        source = inspect.getsource(run_check)
        count = source.count("check_all(")
        assert count == 1, (
            f"check_all() should be called once, found {count} occurrences"
        )


# --- Decision 3: venv-logging-level ---


class TestVenvLoggingLevel:
    """project-venv and no-venv must use log.debug (not log.info).

    Spec decision: venv-logging-level
    """

    def test_venv_events_at_debug_level(self, tmp_path):
        """project-venv and no-venv events are emitted at debug level."""
        project = _make_project(tmp_path, ("comp.py", "def f(): pass\n"))
        captured = _run_and_capture(paths=[project])

        venv_events = _events_by_id(captured, "project-venv")
        no_venv_events = _events_by_id(captured, "no-venv")
        all_venv = venv_events + no_venv_events

        assert len(all_venv) >= 1, "Expected at least one venv event"
        for evt in all_venv:
            assert evt["log_level"] == "debug", (
                f"Event '{evt['event']}' should be debug level, got {evt['log_level']}"
            )

    def test_project_venv_has_kind_and_path(self, tmp_path):
        """project-venv event includes kind and path context keys."""
        source = inspect.getsource(run_check)
        assert '"project-venv"' in source
        assert "kind=" in source
        assert "path=" in source

    def test_no_venv_no_replace_msg(self):
        """no-venv debug event does NOT have _replace_msg (debug events don't need it)."""
        source = inspect.getsource(run_check)
        # Find the no-venv line — should be log.debug("no-venv") without _replace_msg
        lines = source.splitlines()
        no_venv_lines = [line for line in lines if '"no-venv"' in line]
        assert len(no_venv_lines) >= 1
        for line in no_venv_lines:
            assert "_replace_msg" not in line, (
                "no-venv is debug level — should not have _replace_msg"
            )


# --- Decision 4: no-projects-found-level ---


class TestNoProjectsFoundLevel:
    """no-projects-found must use log.warning with _replace_msg and kwargs.

    Spec decision: no-projects-found-level
    """

    def test_emits_no_projects_found(self, tmp_path):
        """Emits no-projects-found event for empty directory."""
        captured = _run_and_capture(paths=[tmp_path])
        assert "no-projects-found" in _event_ids(captured)

    def test_no_projects_found_is_warning(self, tmp_path):
        """no-projects-found is emitted at warning level."""
        captured = _run_and_capture(paths=[tmp_path])
        events = _events_by_id(captured, "no-projects-found")
        assert len(events) == 1
        assert events[0]["log_level"] == "warning"

    def test_no_projects_found_has_replace_msg(self, tmp_path):
        """no-projects-found includes _replace_msg."""
        captured = _run_and_capture(paths=[tmp_path])
        events = _events_by_id(captured, "no-projects-found")
        assert "_replace_msg" in events[0]

    def test_no_projects_found_has_paths_context(self, tmp_path):
        """no-projects-found includes paths kwarg (log-context-required)."""
        captured = _run_and_capture(paths=[tmp_path])
        events = _events_by_id(captured, "no-projects-found")
        assert "paths" in events[0]


# --- Decision 5: component-result-events ---


class TestComponentResultEvents:
    """component-result log.info event must exist with _replace_msg.

    Spec decision: component-result-events
    """

    def test_emits_component_result(self, tmp_path):
        """Emits component-result event per component."""
        project = _make_project(tmp_path, ("comp.py", "def f(): pass\n"))
        captured = _run_and_capture(paths=[project])
        assert "component-result" in _event_ids(captured)

    def test_component_result_is_info_level(self, tmp_path):
        """component-result is emitted at info level."""
        project = _make_project(tmp_path, ("comp.py", "def f(): pass\n"))
        captured = _run_and_capture(paths=[project])
        events = _events_by_id(captured, "component-result")
        assert len(events) >= 1
        assert events[0]["log_level"] == "info"

    def test_component_result_has_replace_msg(self, tmp_path):
        """component-result includes _replace_msg."""
        project = _make_project(tmp_path, ("mycomp.py", "def f(): pass\n"))
        captured = _run_and_capture(paths=[project])
        events = _events_by_id(captured, "component-result")
        assert "_replace_msg" in events[0]

    def test_component_result_has_component_and_passed(self, tmp_path):
        """component-result includes component name and passed flag."""
        project = _make_project(tmp_path, ("mycomp.py", "def f(): pass\n"))
        captured = _run_and_capture(paths=[project])
        events = _events_by_id(captured, "component-result")
        assert events[0]["component"] == "mycomp"
        assert "passed" in events[0]

    def test_component_result_has_status(self, tmp_path):
        """component-result includes status field (passed/failed)."""
        project = _make_project(tmp_path, ("mycomp.py", "def f(): pass\n"))
        captured = _run_and_capture(paths=[project])
        events = _events_by_id(captured, "component-result")
        assert "status" in events[0]


# --- Decision 6: summary-events ---


class TestSummaryEvents:
    """components-failed and components-passed log.info events must exist.

    Spec decision: summary-events
    """

    def test_emits_components_passed(self, tmp_path):
        """Emits components-passed when all components pass."""
        project = _make_project(tmp_path, ("comp.py", "def f(): pass\n"))
        captured = _run_and_capture(paths=[project])
        assert "components-passed" in _event_ids(captured)

    def test_components_passed_is_info_level(self, tmp_path):
        """components-passed is emitted at info level."""
        project = _make_project(tmp_path, ("comp.py", "def f(): pass\n"))
        captured = _run_and_capture(paths=[project])
        events = _events_by_id(captured, "components-passed")
        assert events[0]["log_level"] == "info"

    def test_components_passed_has_replace_msg(self, tmp_path):
        """components-passed includes _replace_msg."""
        project = _make_project(tmp_path, ("comp.py", "def f(): pass\n"))
        captured = _run_and_capture(paths=[project])
        events = _events_by_id(captured, "components-passed")
        assert "_replace_msg" in events[0]

    def test_components_passed_has_count(self, tmp_path):
        """components-passed includes count kwarg."""
        project = _make_project(
            tmp_path,
            ("comp1.py", "def f(): pass\n"),
            ("comp2.py", "def g(): pass\n"),
        )
        captured = _run_and_capture(paths=[project])
        events = _events_by_id(captured, "components-passed")
        assert events[0]["count"] == 2

    def test_components_failed_has_replace_msg(self):
        """components-failed event has _replace_msg in source code."""
        source = inspect.getsource(run_check)
        assert '"components-failed"' in source
        assert "_replace_msg" in source

    def test_components_failed_has_count_and_names(self):
        """components-failed event has count and names context keys."""
        source = inspect.getsource(run_check)
        # Find the components-failed section
        assert "total_failed" in source
        assert "failed_summary" in source


# --- Decision 7: bind-strategy ---


class TestBindStrategy:
    """project key must be set via log.bind() in the project iteration loop.

    Spec decision: bind-strategy
    """

    def test_bind_in_source(self):
        """run_check source contains log.bind(project=...) call."""
        source = inspect.getsource(run_check)
        assert "log.bind" in source
        assert "project=" in source

    def test_project_context_in_checking_components(self, tmp_path):
        """checking-components event has project context from bind."""
        project = _make_project(tmp_path, ("comp.py", "def f(): pass\n"))
        captured = _run_and_capture(paths=[project])
        events = _events_by_id(captured, "checking-components")
        assert len(events) >= 1
        assert "project" in events[0]

    def test_project_context_in_component_result(self, tmp_path):
        """component-result event has project context from bind."""
        project = _make_project(tmp_path, ("comp.py", "def f(): pass\n"))
        captured = _run_and_capture(paths=[project])
        events = _events_by_id(captured, "component-result")
        assert len(events) >= 1
        assert "project" in events[0]

    def test_no_explicit_project_kwarg_on_checking_components(self):
        """checking-components should get project from bind, not explicit kwarg."""
        source = inspect.getsource(run_check)
        lines = source.splitlines()
        for line in lines:
            if "checking-components" in line and "plog" in line:
                # Should use plog (bound logger), and should NOT have project= kwarg
                assert "project=" not in line or "_replace_msg" in line, (
                    "checking-components should get project from bind, not explicit kwarg"
                )


# --- Decision 8: except-block-logging ---


class TestExceptBlockLogging:
    """Except blocks must have log.debug calls.

    Spec decision: except-block-logging
    """

    def test_init_has_version_fallback_log(self):
        """__init__.py except block has log.debug('version-fallback')."""
        import batou_type

        source = inspect.getsource(batou_type)
        assert '"version-fallback"' in source

    def test_init_has_structlog_import(self):
        """__init__.py imports structlog for logging."""
        import batou_type

        source = inspect.getsource(batou_type)
        assert "structlog" in source
        assert "get_logger" in source

    def test_cli_has_stub_not_external_log(self):
        """cli.py _detect_stub except block has log.debug('stub-not-external')."""
        import batou_type.cli as cli_mod

        source = inspect.getsource(cli_mod)
        assert '"stub-not-external"' in source

    def test_stub_not_external_has_name_context(self):
        """stub-not-external event includes name context key."""
        import batou_type.cli as cli_mod

        source = inspect.getsource(cli_mod)
        lines = source.splitlines()
        for line in lines:
            if '"stub-not-external"' in line:
                assert "name=" in line, (
                    "stub-not-external should include name context key"
                )


# --- Decision 9: test-strategy ---


class TestTestStrategy:
    """tests/test_logging.py must exist with log.has() assertions.

    Spec decision: test-strategy
    """

    def test_logging_test_file_exists(self):
        """tests/test_logging.py exists."""
        from pathlib import Path

        test_file = Path(__file__).parent.parent / "test_logging.py"
        assert test_file.exists(), "tests/test_logging.py must exist"

    def test_logging_file_has_event_assertions(self):
        """tests/test_logging.py has assertions for event IDs."""
        from pathlib import Path

        test_file = Path(__file__).parent.parent / "test_logging.py"
        content = test_file.read_text()

        # Must test the key event IDs from the spec event catalog
        required_events = [
            "no-projects-found",
            "projects-found",
            "checking-components",
            "component-result",
            "components-passed",
        ]
        for event_id in required_events:
            assert event_id in content, (
                f"tests/test_logging.py must assert event '{event_id}'"
            )

    def test_logging_file_uses_capture_logs(self):
        """tests/test_logging.py uses structlog capture_logs for in-process testing."""
        from pathlib import Path

        test_file = Path(__file__).parent.parent / "test_logging.py"
        content = test_file.read_text()
        assert "capture_logs" in content
        assert "run_check" in content

    def test_logging_file_tests_event_levels(self):
        """tests/test_logging.py verifies log levels for events."""
        from pathlib import Path

        test_file = Path(__file__).parent.parent / "test_logging.py"
        content = test_file.read_text()
        assert "log_level" in content
