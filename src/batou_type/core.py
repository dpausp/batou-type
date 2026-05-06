# ruff: noqa: E402

"""Core type checking logic shared between CLI and pytest plugin."""

import os
import subprocess  # nosec B404
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from batou_type.output import Diagnostic


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
        [
            str(appenv),
            "python",
            "-c",
            "import sysconfig; print(sysconfig.get_path('purelib'))",
        ],
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


class CheckerError(Exception):
    """Raised when a type checker itself fails (not installed, crash, etc.)."""


@dataclass
class TypeCheckResult:
    """Result of type checking a single file."""

    path: str
    has_errors: bool
    output: str
    command: str = ""
    errors: list[Diagnostic] | None = None


def is_batou_project(directory: Path) -> bool:
    """Check whether a directory looks like a batou project."""
    return (directory / "components").is_dir()


def find_components(root: Path) -> list[Path]:
    """Find all Python files in the components directory."""
    components_dir = root / "components"
    if not components_dir.exists():
        return []
    return sorted(components_dir.glob("**/*.py"))


def ensure_checker_available(checker: Checker) -> None:
    """Verify a type checker is installed and runnable.

    Raises CheckerError if the checker cannot be invoked.
    """
    cmd = [sys.executable, "-m", checker.value, "--version"]
    result = subprocess.run(cmd, capture_output=True, text=True)  # nosec B603
    if result.returncode != 0:
        stderr = result.stderr.strip()
        raise CheckerError(f"Type checker '{checker.value}' is not available: {stderr}")


def check_file(
    file_path: str,
    checkers: list[Checker] | None = None,
    cwd: Path | None = None,
    extra_search_paths: list[str] | None = None,
    ty_args: list[str] | None = None,
    json_mode: bool = False,
) -> TypeCheckResult:
    """Run type checker(s) on a single file.

    Raises CheckerError if the checker itself fails (crash, not installed).
    """
    checkers = checkers or [Checker.ty]
    cwd = cwd or Path.cwd()
    extra_search_paths = extra_search_paths or []
    ty_args = ty_args or []

    env = os.environ.copy()
    if extra_search_paths:
        existing = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = os.pathsep.join(
            extra_search_paths + ([existing] if existing else [])
        )

    full_output = []
    any_failed = False
    display_command = ""
    checker_results: list[tuple[Checker, str, str]] = []

    for c in checkers:
        if c == Checker.ty:
            if json_mode:
                cmd = [sys.executable, "-m", "ty", "check", "--output-format", "gitlab"]
            else:
                cmd = [sys.executable, "-m", "ty", "check", "--color", "always"]
            for sp in extra_search_paths:
                cmd.extend(["--extra-search-path", sp])
            cmd.extend(ty_args)
            cmd.append(file_path)
        else:
            base_cmd = list(CHECKER_COMMANDS[c])
            if json_mode and c == Checker.mypy:
                base_cmd.extend(["--output", "json"])
            cmd = [sys.executable, "-m", *base_cmd, file_path]

        display_command = " ".join(cmd).replace(sys.executable, "python", 1)

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, env=env)  # nosec B603

        # Checker crash: stderr present, no stdout → checker itself failed
        if (
            result.returncode != 0
            and result.stderr.strip()
            and not result.stdout.strip()
        ):
            raise CheckerError(
                f"Type checker '{c.value}' crashed: {result.stderr.strip()}"
            )

        if result.returncode != 0:
            any_failed = True

        # Always collect output so warnings are preserved even on exit 0
        if result.stdout:
            full_output.append(result.stdout)
        if result.stderr:
            full_output.append(result.stderr)

        if json_mode:
            checker_results.append((c, result.stdout, result.stderr))

    if json_mode and any_failed:
        from batou_type.output import from_ty_gitlab, from_mypy_jsonl

        parsed_errors: list[Diagnostic] = []
        for c, stdout, _stderr in checker_results:
            if c == Checker.ty:
                parsed_errors.extend(from_ty_gitlab(stdout))
            elif c == Checker.mypy:
                parsed_errors.extend(from_mypy_jsonl(stdout))

        return TypeCheckResult(
            path=file_path,
            has_errors=any_failed,
            output="".join(full_output),
            command=display_command,
            errors=parsed_errors,
        )

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
    ty_args: list[str] | None = None,
    json_mode: bool = False,
) -> list[TypeCheckResult]:
    """Type check all component files in a deployment."""
    checkers = checkers or [Checker.ty]
    extra_search_paths = list(extra_search_paths or [])
    ty_args = ty_args or []

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
        result = check_file(
            rel_path,
            checkers,
            root,
            extra_search_paths=extra_search_paths,
            ty_args=ty_args,
            json_mode=json_mode,
        )
        results.append(result)

    return results
