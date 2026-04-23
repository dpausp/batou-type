"""Type-check batou deployments against batou stubs - CLI entry point."""

import sys
from importlib import metadata
from importlib.resources import files
from pathlib import Path

import typer

from batou_typecheck.core import Checker, check_all, find_components

app = typer.Typer(rich_markup_mode="none")
echo = typer.echo


@app.command()
def main(
    checker: list[Checker] = typer.Option(
        [],
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
            echo(f"[batou-typecheck] {stub} {version}")
        except Exception:
            echo(f"[batou-typecheck] {stub} <not installed>")
            continue

        # Try to get path
        try:
            pkg = stub.replace("-stubs", "")
            stub_path = str(files(pkg).joinpath("lib").parent)
            echo(f"[batou-typecheck]   {stub_path}")
        except Exception:
            pass

    checkers = checker or [Checker.ty]

    cwd = Path.cwd()
    components = find_components(cwd)

    if not components:
        print("batou-typecheck: No component files found in components/", file=sys.stderr)
        raise typer.Exit(0)

    echo(f"batou-typecheck: Checking {len(components)} component(s)")

    # Check all files
    results = check_all(cwd, checkers)

    # Count errors
    failed_results = [r for r in results if r.has_errors]
    echo(f"batou-typecheck: {len(failed_results)} file(s) with errors")

    # Show errors at end (pytest-style)
    for result in failed_results:
        echo(f"\n{'='*60}")
        echo(f"FAILED: {result.path}")
        echo(f"{'='*60}")
        if result.output.strip():
            echo(result.output)

    raise typer.Exit(1 if failed_results else 0)