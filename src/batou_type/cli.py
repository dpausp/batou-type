"""Batou type CLI."""

from dataclasses import dataclass
from importlib import metadata
from importlib.resources import files
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from batou_type import __version__
from batou_type.core import Checker, TypeCheckResult, check_all, find_components, is_batou_project

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


def _run_check(checker: list[Checker] | None, paths: list[Path]) -> None:
    """Execute type checking."""
    # Show stub versions and paths
    table = Table(title="Loaded stubs", show_header=False, box=None)
    table.add_column(style="dim")

    stub_infos = get_stub_versions()
    extra_search_paths: list[str] = []
    for info in stub_infos:
        if info.version and info.path:
            table.add_row(f"[cyan]{info.name}[/] [dim]{info.version}[/] @ [dim]{info.path}[/]")
            extra_search_paths.append(str(Path(info.path).parent))
        else:
            table.add_row(f"[yellow]{info.name}[/] [dim]<not installed>[/]")

    console.print(table)
    console.print()

    # Discover batou projects
    projects = [p for p in paths if is_batou_project(p)]
    if not projects:
        console.print("[yellow]No batou projects found (need components/ directory)[/]")
        raise typer.Exit(0)

    console.print(f"[green]Found {len(projects)} project(s):[/]")
    for project in projects:
        console.print(f"  [dim]{project}[/]")
    console.print()

    checkers = checker or [Checker.ty]
    all_failed: list[TypeCheckResult] = []

    for project in projects:
        components = find_components(project)
        if not components:
            continue

        console.print(f"[green]Checking {len(components)} component(s) in {project}...[/]")
        results = check_all(project, checkers, extra_search_paths=extra_search_paths)

        # Show errors for this project
        for result in results:
            if result.has_errors:
                all_failed.append(result)
                console.print(f"\n[red]{'=' * 60}[/]")
                console.print(f"[red]FAILED: {result.path}[/]")
                console.print(f"[red]{'=' * 60}[/]")
                if result.output.strip():
                    print(result.output.strip())

    # Summary at the bottom
    if all_failed:
        console.print()
        status = f"[red]{len(all_failed)}[/]"
        console.print(f"{status} component(s) with errors:")
        for result in all_failed:
            console.print(f"  [red]{result.path}[/]")
    else:
        console.print("[green]All components passed type checking.[/]")

    raise typer.Exit(1 if all_failed else 0)


@app.command()
def check(
    paths: list[Path] = typer.Argument(
        ...,
        help="Project directories to check (default: current directory)",
    ),
    checker: list[Checker] | None = typer.Option(
        None,
        "--checker",
        "-c",
        help="Type checker(s) to run (default: ty)",
    ),
) -> None:
    """Type-check batou deployment components."""
    _run_check(checker, paths)
