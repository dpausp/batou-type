"""Type-check batou deployments against batou stubs."""

import json
import subprocess
import sys
from enum import Enum
from pathlib import Path
from typing import Annotated

import typer

# basedpyright diagnostics that are noise for batou components (always false positives)
BASEDPYRIGHT_NOISE_RULES = frozenset(
    {
        "reportUninitializedInstanceVariable",
        "reportImplicitOverride",
        "reportUnannotatedClassAttribute",
    }
)


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

app = typer.Typer()


def _filter_basedpyright_json(output: str) -> tuple[str, bool]:
    """Filter basedpyright JSON output, removing noise diagnostics.

    Returns (human-readable filtered output, has_real_errors).
    """
    try:
        data = json.loads(output)
    except json.JSONDecodeError:
        # Fallback: not JSON, return raw
        return output, "error" in output.lower()

    general = data.get("generalDiagnostics", [])
    filtered = [
        d for d in general if d.get("rule") not in BASEDPYRIGHT_NOISE_RULES
    ]
    has_errors = any(d.get("severity") == "error" for d in filtered)

    if not filtered:
        return "", False

    # Reconstruct human-readable output for the filtered diagnostics
    lines: list[str] = []
    # Group by file
    by_file: dict[str, list[dict]] = {}
    for d in filtered:
        f = d.get("file", "<unknown>")
        by_file.setdefault(f, []).append(d)

    for file_path, diags in by_file.items():
        lines.append(file_path)
        for d in diags:
            loc = f":{d.get('range', {}).get('start', {}).get('line', '?') + 1}"
            severity = d.get("severity", "unknown")
            rule = d.get("rule", "")
            message = d.get("message", "")
            lines.append(f"  {file_path}{loc} - {severity}: {message} ({rule})")
        errors = sum(1 for d in diags if d.get("severity") == "error")
        warnings = sum(1 for d in diags if d.get("severity") == "warning")
        notes = sum(1 for d in diags if d.get("severity") == "information")
        lines.append(
            f"{errors} error{'s' if errors != 1 else ''}, "
            f"{warnings} warning{'s' if warnings != 1 else ''}, "
            f"{notes} note{'s' if notes != 1 else ''}"
        )

    return "\n".join(lines), has_errors


@app.command()
def main(
    checker: Annotated[
        list[Checker],
        typer.Option(
            "--checker",
            "-c",
            help="Type checker(s) to run (default: ty)",
        ),
    ] = [],
) -> None:
    """Type-check batou deployment components."""
    checkers = checker or [Checker.ty]

    cwd = Path.cwd()
    components = sorted(cwd.glob("components/**/*.py"))

    if not components:
        print("No component files found in components/", file=sys.stderr)
        raise typer.Exit(0)

    paths = [str(p) for p in components]
    print(
        f"Type-checking {len(components)} component file(s) ...",
        file=sys.stderr,
    )

    any_failed = False
    for c in checkers:
        print(f"--- {c.value} ---", file=sys.stderr)
        for path in paths:
            cmd = [*CHECKER_COMMANDS[c], path]
            if c == Checker.basedpyright:
                result = subprocess.run(cmd, capture_output=True, text=True)
                filtered, has_errors = _filter_basedpyright_json(result.stdout)
                if filtered.strip():
                    print(filtered)
                if has_errors:
                    any_failed = True
            else:
                result = subprocess.run(cmd)
                if result.returncode != 0:
                    any_failed = True

    raise typer.Exit(1 if any_failed else 0)
