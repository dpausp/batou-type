"""Core type checking logic shared between CLI and pytest plugin."""

import subprocess  # nosec B404
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

# Venv detection patterns, ordered by priority
_VENV_CANDIDATES = [".venv", "appenv"]


def find_project_venv(project: Path) -> Path | None:
    """Detect a project-level venv (.venv for uv, appenv for batou)."""
    for candidate in _VENV_CANDIDATES:
        venv_dir = project / candidate
        if venv_dir.is_dir():
            # Verify it looks like a venv: has a site-packages or pyvenv.cfg
            if (venv_dir / "pyvenv.cfg").exists() or (venv_dir / "lib").is_dir():
                return venv_dir
    return None


def get_venv_site_packages(venv: Path) -> list[str]:
    """Extract site-packages paths from a venv."""
    paths: list[str] = []
    # Standard layout: lib/pythonX.Y/site-packages
    for sp in sorted(venv.glob("lib/python*/site-packages")):
        paths.append(str(sp))
    # lib64 symlink (some Linux distros)
    for sp in sorted(venv.glob("lib64/python*/site-packages")):
        p = str(sp)
        if p not in paths:
            paths.append(p)
    return paths


class Checker(str, Enum):
    ty = "ty"
    mypy = "mypy"


CHECKER_COMMANDS: dict[Checker, list[str]] = {
    Checker.ty: ["ty", "check"],
    Checker.mypy: [
        "mypy",
        "--explicit-package-bases",
        "--check-untyped-defs",
        "--no-incremental",
    ],
}


@dataclass
class TypeCheckResult:
    """Result of type checking a single file."""

    path: str
    has_errors: bool
    output: str


def is_batou_project(directory: Path) -> bool:
    """Check whether a directory looks like a batou project."""
    return (directory / "components").is_dir()


def find_components(root: Path) -> list[Path]:
    """Find all component files in the components directory."""
    components_dir = root / "components"
    if not components_dir.exists():
        return []
    return sorted(components_dir.glob("**/*.py"))


def check_file(
    file_path: str,
    checkers: list[Checker] | None = None,
    cwd: Path | None = None,
    extra_search_paths: list[str] | None = None,
) -> TypeCheckResult:
    """Run type checker(s) on a single file."""
    checkers = checkers or [Checker.ty]
    cwd = cwd or Path.cwd()
    extra_search_paths = extra_search_paths or []

    full_output = []
    any_failed = False

    for c in checkers:
        if c == Checker.ty:
            cmd = [sys.executable, "-m", "ty", "check", "--color", "always"]
            for sp in extra_search_paths:
                cmd.extend(["--extra-search-path", sp])
            cmd.append(file_path)
        else:
            cmd = [
                sys.executable,
                "-m",
                *CHECKER_COMMANDS[c],
                file_path,
            ]

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)  # nosec B603
        if result.returncode != 0:
            any_failed = True
            if result.stdout:
                full_output.append(result.stdout)
            if result.stderr:
                full_output.append(result.stderr)

    return TypeCheckResult(
        path=file_path,
        has_errors=any_failed,
        output="".join(full_output),
    )


def check_all(
    root: Path,
    checkers: list[Checker] | None = None,
    extra_search_paths: list[str] | None = None,
) -> list[TypeCheckResult]:
    """Type check all component files in a deployment."""
    checkers = checkers or [Checker.ty]

    components = find_components(root)
    results = []

    for component in components:
        rel_path = str(component.relative_to(root))
        result = check_file(rel_path, checkers, root, extra_search_paths=extra_search_paths)
        results.append(result)

    return results

