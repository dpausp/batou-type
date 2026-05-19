"""E2E test fixtures and helpers."""
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

import pytest


_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
BATOU_TYPE_CLI = [sys.executable, "-m", "batou_type"]

# Component that triggers unresolved-attribute via self._ usage.
SELF_DEREF_COMPONENT = """\
from batou.component import Component


class SubComp(Component):
    address: str = "localhost"


class MyComp(Component):
    address: str

    def configure(self):
        self += SubComp()
        addr = self._.address
"""


@pytest.fixture
def temp_project(tmp_path: Path) -> Path:
    """Create a temporary batou project with components directory."""
    components = tmp_path / "components"
    components.mkdir()
    return tmp_path


@pytest.fixture
def run_cli() -> Callable[..., subprocess.CompletedProcess[str]]:
    """Fixture providing run_cli helper."""
    def _run_cli(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env.pop("JOURNAL_STREAM", None)
        return subprocess.run(
            [*BATOU_TYPE_CLI, *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            env=env,
        )
    return _run_cli


@pytest.fixture
def extract_json() -> Callable[[str], dict[str, Any]]:
    """Fixture providing extract_json helper."""
    def _extract_json(stdout: str) -> dict[str, Any]:
        """Extract JSON object from stdout, stripping non-JSON prefix lines."""
        start = stdout.index("{")
        return json.loads(stdout[start:])
    return _extract_json


@pytest.fixture
def strip_ansi() -> Callable[[str], str]:
    """Fixture providing strip_ansi helper."""
    def _strip_ansi(text: str) -> str:
        """Remove ANSI escape codes from text."""
        return _ANSI_RE.sub("", text)
    return _strip_ansi


@pytest.fixture
def strip_stogger_lines() -> Callable[[str], str]:
    """Fixture providing strip_stogger_lines helper."""
    def _strip_stogger_lines(output: str) -> str:
        """Remove stogger debug/info prefix lines from CLI output."""
        return "\n".join(
            line
            for line in output.splitlines()
            if not line.startswith("20")
        )
    return _strip_stogger_lines
