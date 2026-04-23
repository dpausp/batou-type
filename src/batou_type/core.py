"""Core type checking logic shared between CLI and pytest plugin."""

import io
import json
import subprocess
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class Checker(str, Enum):
    ty = "ty"
    mypy = "mypy"
    basedpyright = "basedpyright"


CHECKER_COMMANDS: dict[Checker, list[str]] = {
    Checker.ty: ["ty", "check"],
    Checker.mypy: [
        "mypy",
        "--explicit-package-bases",
        "--check-untyped-defs",
        "--no-incremental",
    ],
    Checker.basedpyright: ["basedpyright", "--outputjson"],
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
        elif c == Checker.mypy:
            cmd = [
                sys.executable,
                "-m",
                "mypy",
                *CHECKER_COMMANDS[c][1:],
                file_path,
            ]
        elif c == Checker.basedpyright:
            cmd = [
                sys.executable,
                "-m",
                "basedpyright",
                *CHECKER_COMMANDS[c][1:],
                file_path,
            ]

        if c == Checker.basedpyright:
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)
            filtered, has_errors = _filter_basedpyright_json(result.stdout)
            if filtered.strip():
                full_output.append(filtered)
            if has_errors:
                any_failed = True
        else:
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


# basedpyright diagnostics that are noise for batou components
BASEDPYRIGHT_NOISE_RULES = frozenset(
    {
        "reportUninitializedInstanceVariable",
        "reportImplicitOverride",
        "reportUnannotatedClassAttribute",
    }
)


def _filter_basedpyright_json(output: str) -> tuple[str, bool]:
    """Filter basedpyright JSON output, removing noise rules."""
    try:
        data = json.loads(output)
    except json.JSONDecodeError:
        return output, bool(output.strip())

    if not isinstance(data, dict):
        return output, bool(output.strip())

    # Basedpyright outputs diagnostics under "generalDiagnostics" or similar
    diagnostics = data.get("generalDiagnostics", [])

    filtered = [
        d for d in diagnostics if d.get("rule", "") not in BASEDPYRIGHT_NOISE_RULES
    ]

    if not filtered:
        return "", False

    # Rebuild output with filtered diagnostics
    data["generalDiagnostics"] = filtered

    buffer = io.StringIO()
    buffer.write(json.dumps(data, indent=2))
    return buffer.getvalue(), True
