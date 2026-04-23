"""Batou type CLI."""

from dataclasses import dataclass
from importlib import metadata
from importlib.resources import files
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from batou_type import __version__
from batou_type.core import Checker, check_all, find_components

app = typer.Typer(
    no_args_is_help=True,
    rich_markup_mode="rich",
)
console = Console()

STUB_PACKAGES = ["batou-stubs", "batou_ext-stubs"]


@dataclass(slots=True)
class StubInfo:
    """Version metadata for a stub package."""

    name: str
    version: str | None
    path: str | None


def get_stub_versions() -> list[StubInfo]:
    """Collect version and path for all stub packages."""
    infos: list[StubInfo] = []
    for name in STUB_PACKAGES:
        try:
            ver = metadata.version(name)
            pkg = name.replace("-stubs", "")
            stub_path = str(files(pkg).joinpath("lib").parent)  # type: ignore[unresolved-attribute]
        except Exception:
            infos.append(StubInfo(name=name, version=None, path=None))
        else:
            infos.append(StubInfo(name=name, version=ver, path=stub_path))
    return infos


@app.command()
def version() -> None:
    """Show version information."""
    console.print(f"batou-type [cyan]{__version__}[/]")
    for info in get_stub_versions():
        if info.version:
            console.print(f"  [cyan]{info.name}[/] [dim]{info.version}[/] @ [dim]{info.path}[/]")
        else:
            console.print(f"  [yellow]{info.name}[/] [dim]<not installed>[/]")


def _run_check(checker: list[Checker] | None) -> None:
    """Execute type checking."""
    # Show stub versions and paths
    table = Table(title="Loaded stubs", show_header=False, box=None)
    table.add_column(style="dim")

    for info in get_stub_versions():
        if info.version:
            table.add_row(f"[cyan]{info.name}[/] [dim]{info.version}[/] @ [dim]{info.path}[/]")
        else:
            table.add_row(f"[yellow]{info.name}[/] [dim]<not installed>[/]")

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
    status = f"[red]{len(failed_results)}[/]" if failed_results else "[green]0[/]"
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
