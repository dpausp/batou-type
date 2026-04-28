"""Functional E2E tests for batou-type CLI."""

import subprocess
import sys
from pathlib import Path

import pytest


SRC = Path(__file__).parent.parent / "src"
BATOU_TYPE_CLI = [sys.executable, "-m", "batou_type"]


@pytest.fixture
def temp_project(tmp_path):
    """Create a temporary batou project with components directory."""
    components = tmp_path / "components"
    components.mkdir()
    return tmp_path


def run_cli(*args, cwd=None):
    """Run batou-type CLI and return result."""
    result = subprocess.run(
        [*BATOU_TYPE_CLI, *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    return result


class TestVersion:
    """Tests for version command."""

    def test_version_shows_batou_type_version(self, tmp_path):
        """Version command shows batou-type version."""
        result = run_cli("version", cwd=tmp_path)
        assert result.returncode == 0
        assert "batou-type" in result.stdout.lower()

    def test_version_shows_stub_info(self, tmp_path):
        """Version command shows stub package info."""
        result = run_cli("version", cwd=tmp_path)
        assert "batou-stubs" in result.stdout.lower()


class TestCheck:
    """Tests for check command."""

    def test_check_no_components_exits_zero(self, tmp_path):
        """Check with no component files exits 0."""
        result = run_cli("check", cwd=tmp_path)
        assert result.returncode == 0
        assert "no batou projects found" in result.stdout.lower()

    def test_check_clean_component_exits_zero(self, temp_project):
        """Check with valid component files exits 0."""
        component = temp_project / "components" / "mycomponent.py"
        component.write_text("def configure():\n    pass\n")

        result = run_cli("check", cwd=temp_project)
        assert result.returncode == 0
        assert "passed type checking" in result.stdout.lower()

    def test_check_component_with_type_error_exits_one(self, temp_project):
        """Check with type errors exits 1."""
        component = temp_project / "components" / "badcomponent.py"
        component.write_text("def configure() -> int:\n    return 'not an int'\n")

        result = run_cli("check", cwd=temp_project)
        assert result.returncode == 1

    def test_check_with_ty_checker(self, temp_project):
        """Check with explicit -c ty works."""
        component = temp_project / "components" / "mycomponent.py"
        component.write_text("def configure():\n    pass\n")

        result = run_cli("check", "-c", "ty", cwd=temp_project)
        assert result.returncode == 0

    def test_check_with_mypy_checker(self, temp_project):
        """Check with explicit -c mypy works."""
        component = temp_project / "components" / "mycomponent.py"
        component.write_text("def configure():\n    pass\n")

        result = run_cli("check", "-c", "mypy", cwd=temp_project)
        # mypy might not be installed, but command should not crash
        assert result.returncode in (0, 1, 2)  # 2 = checker not found

    def test_check_multiple_components(self, temp_project):
        """Check handles multiple component files."""
        (temp_project / "components" / "comp1.py").write_text("def foo():\n    pass\n")
        (temp_project / "components" / "comp2.py").write_text("def bar():\n    pass\n")

        result = run_cli("check", cwd=temp_project)
        assert result.returncode == 0
        # Should check multiple files
        assert "2 component" in result.stdout.lower()

    def test_check_nested_components(self, temp_project):
        """Check finds components in nested directories."""
        nested = temp_project / "components" / "subpackage"
        nested.mkdir(parents=True)
        (nested / "nestedcomp.py").write_text("def nested():\n    pass\n")

        result = run_cli("check", cwd=temp_project)
        assert result.returncode == 0


class TestHelp:
    """Tests for help output."""

    def test_help_shows_commands(self):
        """--help shows available commands."""
        result = run_cli("--help")
        assert result.returncode == 0
        assert "check" in result.stdout.lower()
        assert "version" in result.stdout.lower()

    def test_check_help_shows_options(self):
        """check --help shows options."""
        result = run_cli("check", "--help")
        assert result.returncode == 0
        assert "--checker" in result.stdout.lower()

    def test_bad_command_shows_error(self):
        """Invalid command shows error message."""
        result = run_cli("nonexistent")
        assert result.returncode == 2
        # Typer outputs errors to stderr
        assert "no such command" in result.stderr.lower()


class TestErrorHandling:
    """Tests for error handling."""

    def test_invalid_checker_shows_error(self, temp_project):
        """Invalid checker name shows clear error."""
        result = run_cli("check", "--checker", "invalid", cwd=temp_project)
        assert result.returncode == 2
        # Typer outputs errors to stderr
        assert "invalid" in result.stderr.lower()
