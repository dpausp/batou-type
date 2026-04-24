"""Core type checking logic shared between CLI and pytest plugin."""

import subprocess
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


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
) -> TypeCheckResult:
    """Run type checker(s) on a single file."""
    checkers = checkers or [Checker.ty]
    cwd = cwd or Path.cwd()

    full_output = []
    any_failed = False

    for c in checkers:
        if c == Checker.ty:
            cmd = [sys.executable, "-m", "ty", "check", "--color", "always", file_path]
        else:
            cmd = [
                sys.executable,
                "-m",
                *CHECKER_COMMANDS[c],
                file_path,
            ]

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
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
) -> list[TypeCheckResult]:
    """Type check all component files in a deployment."""
    checkers = checkers or [Checker.ty]

    components = find_components(root)
    results = []

    for component in components:
        rel_path = str(component.relative_to(root))
        result = check_file(rel_path, checkers, root)
        results.append(result)

    return results

