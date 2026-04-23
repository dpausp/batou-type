"""Batou type CLI."""

from importlib import metadata
from importlib.resources import files
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from batou_type.core import Checker, check_all, find_components

app = typer.Typer(
    no_args_is_help=True,
    rich_markup_mode="rich",
)
console = Console()


def _run_check(checker: list[Checker] | None) -> None:
    """Execute type checking."""
    # Show stub versions and paths
    table = Table(title="Loaded stubs", show_header=False, box=None)
    table.add_column(style="dim")

    for stub in ["batou-stubs", "batou_ext-stubs"]:
        try:
            version = metadata.version(stub)
            pkg = stub.replace("-stubs", "")
            stub_path = str(files(pkg).joinpath("lib").parent)
            table.add_row(f"[cyan]{stub}[/] [dim]{version}[/] @ [dim]{stub_path}")
        except Exception:
            table.add_row(f"[yellow]{stub}[/] [dim]<not installed>")

    console.print(table)
    console.print()

    checkers = checker or [Checker.ty]

    cwd = Path.cwd()
    components = find_components(cwd)

    if not components:
        console.print("[yellow]No component files found in components/[/]")
        raise typer.Exit(0)

    console.print(f"[green]Checking {len(components)} component(s)...[/]")

    # Check all files
    results = check_all(cwd, checkers)

    # Count errors
    failed_results = [r for r in results if r.has_errors]
    status = f"[red]{len(failed_results)}[/]" if failed_results else f"[green]0[/]"
    console.print(f"{status} file(s) with errors")

    # Show errors at end (pytest-style)
    for result in failed_results:
        console.print(f"\n[red]{'=' * 60}[/]")
        console.print(f"[red]FAILED: {result.path}[/]")
        console.print(f"[red]{'=' * 60}[/]")
        if result.output.strip():
            console.print(result.output)

    raise typer.Exit(1 if failed_results else 0)


@app.command()
def check(
    checker: list[Checker] | None = typer.Option(
        None,
        "--checker",
        "-c",
        help="Type checker(s) to run (default: ty)",
    ),
) -> None:
    """Type-check batou deployment components."""
    _run_check(checker)
