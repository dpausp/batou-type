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

app = typer.Typer(rich_markup_mode="none")


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
    from importlib import metadata

    # Show stub versions
    for stub in ["batou-stubs", "batou_ext-stubs"]:
        try:
            version = metadata.version(stub)
            _sys.stderr.write(f"[batou-typecheck] {stub} {version}\n")
        except Exception:
            _sys.stderr.write(f"[batou-typecheck] {stub} <not installed>\n")

    _sys.stderr.flush()

    checkers = checker or [Checker.ty]

    cwd = Path.cwd()
    components = sorted(cwd.glob("components/**/*.py"))

    if not components:
        print("batou-typecheck: No component files found in components/", file=sys.stderr)
        raise typer.Exit(0)

    paths = [str(p) for p in components]
    print(
        f"batou-typecheck: Checking {len(components)} component(s) with {', '.join(c.value for c in checkers)}",
        file=sys.stderr,
    )
    print("---", file=sys.stderr)

    any_failed = False
    total_errors = 0

    for path in paths:
        file_failed = False
        print(f"[batou-typecheck] {path}", file=sys.stderr)

        for c in checkers:
            if c == Checker.ty:
                cmd = [sys.executable, "-m", "ty", "check", path]
            elif c == Checker.mypy:
                cmd = [
                    sys.executable,
                    "-m",
                    "mypy",
                    *CHECKER_COMMANDS[c][1:],
                    path,
                ]
            else:
                cmd = [*CHECKER_COMMANDS[c], path]

            if c == Checker.basedpyright:
                result = subprocess.run(cmd, capture_output=True, text=True)
                filtered, has_errors = _filter_basedpyright_json(result.stdout)
                if filtered.strip():
                    print(filtered)
                if has_errors:
                    file_failed = True
                    any_failed = True
            else:
                result = subprocess.run(cmd)
                if result.returncode != 0:
                    file_failed = True
                    any_failed = True

        status = "FAILED" if file_failed else "OK"
        print(f"[batou-typecheck] {path} → {status}", file=sys.stderr)
        if file_failed:
            total_errors += 1

    print("---", file=sys.stderr)
    print(
        f"batou-typecheck: {total_errors} file(s) with errors",
        file=sys.stderr,
    )

    raise typer.Exit(1 if any_failed else 0)
