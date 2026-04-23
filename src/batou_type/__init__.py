"""Batou type CLI."""

import sys
from importlib import metadata
from importlib.resources import files
from pathlib import Path

import typer

from batou_type.core import Checker, check_all, find_components

app = typer.Typer(name="batou-type", invoke_without_command=True)
echo = typer.echo


@app.callback()
def check(
    checker: list[Checker] | None = typer.Option(
        None,
        "--checker",
        "-c",
        help="Type checker(s) to run (default: ty)",
    ),
) -> None:
    """Type-check batou deployment components."""
    # Show stub versions and paths
    for stub in ["batou-stubs", "batou_ext-stubs"]:
        try:
            version = metadata.version(stub)
            echo(f"[batou] {stub} {version}")
        except Exception:
            echo(f"[batou] {stub} <not installed>")
            continue

        # Try to get path
        try:
            pkg = stub.replace("-stubs", "")
            stub_path = str(files(pkg).joinpath("lib").parent)
            echo(f"[batou]   {stub_path}")
        except Exception:
            pass

    checkers = checker or [Checker.ty]

    cwd = Path.cwd()
    components = find_components(cwd)

    if not components:
        print("batou: No component files found in components/", file=sys.stderr)
        raise typer.Exit(0)

    echo(f"batou: Checking {len(components)} component(s)")

    # Check all files
    results = check_all(cwd, checkers)

    # Count errors
    failed_results = [r for r in results if r.has_errors]
    echo(f"batou: {len(failed_results)} file(s) with errors")

    # Show errors at end (pytest-style)
    for result in failed_results:
        print(f"\n{'='*60}")
        print(f"FAILED: {result.path}")
        print(f"{'='*60}")
        if result.output.strip():
            print(result.output)

    raise typer.Exit(1 if failed_results else 0)