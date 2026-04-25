"""Core type checking logic shared between CLI and pytest plugin."""

import os
import subprocess  # nosec B404
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

@dataclass(frozen=True)
class VenvInfo:
    """Detected venv information."""

    label: str  # e.g. ".venv" or "appenv"
    path: str  # venv dir or appenv script path
    site_packages: list[str]
    is_appenv: bool = False


def _detect_dotvenv(project: Path) -> VenvInfo | None:
    """Detect a standard .venv directory."""
    venv_dir = project / ".venv"
    if not venv_dir.is_dir():
        return None
    if not ((venv_dir / "pyvenv.cfg").exists() or (venv_dir / "lib").is_dir()):
        return None
    return VenvInfo(
        label=".venv",
        path=str(venv_dir),
        site_packages=_glob_site_packages(venv_dir),
    )


def _detect_appenv(project: Path) -> VenvInfo | None:
    """Detect an appenv script and resolve its site-packages via ./appenv python."""
    appenv = project / "appenv"
    if not appenv.is_file():
        return None
    result = subprocess.run(  # nosec B603
        [str(appenv), "python", "-c", "import sysconfig; print(sysconfig.get_path('purelib'))"],
        capture_output=True,
        text=True,
        cwd=project,
    )
    if result.returncode != 0:
        return None
    site_packages = result.stdout.strip()
    if not site_packages:
        return None
    return VenvInfo(
        label="appenv",
        path=str(appenv),
        site_packages=[site_packages],
        is_appenv=True,
    )


def find_project_venv(project: Path) -> VenvInfo | None:
    """Detect a project-level venv (.venv for uv, appenv for batou)."""
    return _detect_dotvenv(project) or _detect_appenv(project)


def _glob_site_packages(venv: Path) -> list[str]:
    """Extract site-packages paths from a standard venv directory."""
    paths: list[str] = []
    for sp in sorted(venv.glob("lib/python*/site-packages")):
        paths.append(str(sp))
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
    command: str = ""


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

    env = os.environ.copy()
    if extra_search_paths:
        existing = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = os.pathsep.join(extra_search_paths + ([existing] if existing else []))

    full_output = []
    any_failed = False
    display_command = ""

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

        display_command = " ".join(cmd).replace(sys.executable, "python", 1)

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, env=env)  # nosec B603
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
        command=display_command,
    )


def check_all(
    root: Path,
    checkers: list[Checker] | None = None,
    extra_search_paths: list[str] | None = None,
) -> list[TypeCheckResult]:
    """Type check all component files in a deployment."""
    checkers = checkers or [Checker.ty]
    extra_search_paths = list(extra_search_paths or [])

    venv = find_project_venv(root)
    if venv is not None:
        # Convert to relative paths (ty runs with cwd=root)
        extra_search_paths = extra_search_paths + [
            str(Path(sp).relative_to(root)) for sp in venv.site_packages
        ]

    components = find_components(root)
    results = []

    for component in components:
        rel_path = str(component.relative_to(root))
        result = check_file(rel_path, checkers, root, extra_search_paths=extra_search_paths)
        results.append(result)

    return results

