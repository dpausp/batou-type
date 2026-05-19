"""E2E golden-file tests for `batou-type setup`.

Runs the real CLI as subprocess and compares the resulting pyproject.toml
against checked-in golden files. Fails on ANY character difference —
this catches config drift, formatting changes, and missing sections.
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest

GOLDEN_DIR = Path(__file__).resolve().parent / "golden" / "setup"
BATOU_TYPE_CLI = [sys.executable, "-m", "batou_type"]

# Pre-existing pyproject.toml for the "existing project" scenario
EXISTING_PYPROJECT = (
    '[project]\n'
    'name = "example-clean-project"\n'
    'version = "0.1.0"\n'
    'description = "Example batou project with no type errors"\n'
    'dependencies = [\n'
    '    "batou",\n'
    '    "batou_ext",\n'
    '    "boto",\n'
    '    "httpx>=0.28.1",\n'
    ']\n'
    'requires-python = ">=3.12"\n'
)


def _run_setup(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.pop("JOURNAL_STREAM", None)
    return subprocess.run(
        [*BATOU_TYPE_CLI, "setup", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        env=env,
    )


def _normalize_name(text: str, project_dir: Path) -> str:
    """Replace dynamic tmp dir name with stable placeholder."""
    return text.replace(f'name = "{project_dir.name}"', 'name = "TEST_PROJECT_NAME"')


@pytest.fixture
def fresh_project(tmp_path: Path) -> Path:
    """Minimal batou project without pyproject.toml."""
    (tmp_path / "components").mkdir()
    return tmp_path


@pytest.fixture
def existing_project(tmp_path: Path) -> Path:
    """Batou project with existing pyproject.toml containing dependencies."""
    (tmp_path / "components").mkdir()
    (tmp_path / "pyproject.toml").write_text(EXISTING_PYPROJECT)
    return tmp_path


def test_fresh_project_all_checkers(fresh_project: Path) -> None:
    """Setup on fresh project produces golden pyproject.toml (all checkers)."""
    result = _run_setup(str(fresh_project), cwd=fresh_project)
    assert result.returncode == 0, f"CLI failed: {result.stderr}"

    actual = (fresh_project / "pyproject.toml").read_text()
    actual = _normalize_name(actual, fresh_project)
    golden = (GOLDEN_DIR / "fresh_all_checkers.toml").read_text()
    assert actual == golden, (
        f"Golden file mismatch!\n"
        f"--- golden (fresh_all_checkers.toml)\n+++ actual\n"
        f"Use: diff tests/e2e/golden/setup/fresh_all_checkers.toml <(cat {fresh_project}/pyproject.toml | sed 's/{fresh_project.name}/TEST_PROJECT_NAME/')"
    )


def test_existing_project_all_checkers(existing_project: Path) -> None:
    """Setup on project with existing pyproject.toml merges config correctly."""
    result = _run_setup(str(existing_project), cwd=existing_project)
    assert result.returncode == 0, f"CLI failed: {result.stderr}"

    actual = (existing_project / "pyproject.toml").read_text()
    golden = (GOLDEN_DIR / "existing_all_checkers.toml").read_text()
    assert actual == golden, (
        "Golden file mismatch!\n"
        "--- golden (existing_all_checkers.toml)\n+++ actual\n"
    )


def test_fresh_project_ty_only(fresh_project: Path) -> None:
    """Setup with --checkers ty produces ty-only golden pyproject.toml."""
    result = _run_setup("--checkers", "ty", str(fresh_project), cwd=fresh_project)
    assert result.returncode == 0, f"CLI failed: {result.stderr}"

    actual = (fresh_project / "pyproject.toml").read_text()
    actual = _normalize_name(actual, fresh_project)
    golden = (GOLDEN_DIR / "ty_only.toml").read_text()
    assert actual == golden, (
        "Golden file mismatch!\n"
        "--- golden (ty_only.toml)\n+++ actual\n"
    )


def test_idempotent_matches_golden(fresh_project: Path) -> None:
    """Second setup run produces identical output to first run."""
    golden = (GOLDEN_DIR / "fresh_all_checkers.toml").read_text()

    _run_setup(str(fresh_project), cwd=fresh_project)
    first = (fresh_project / "pyproject.toml").read_text()
    first = _normalize_name(first, fresh_project)
    assert first == golden

    _run_setup(str(fresh_project), cwd=fresh_project)
    second = (fresh_project / "pyproject.toml").read_text()
    second = _normalize_name(second, fresh_project)
    assert second == golden
    assert first == second
