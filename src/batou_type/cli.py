"""Batou type CLI."""

from dataclasses import dataclass
from importlib import metadata
from importlib.resources import files
import os
from pathlib import Path
import shlex
import sys

import typer
from rich.console import Console
from rich.text import Text

from batou_type import __version__
from batou_type.core import (
    Checker,
    TypeCheckResult,
    VenvInfo,
    check_all,
    find_components,
    find_project_venv,
    is_batou_project,
)

app = typer.Typer(
    no_args_is_help=True,
    rich_markup_mode="rich",
)
console = Console()

VENDOR_STUBS_PATH = Path(__file__).resolve().parent / "vendor"

VENDOR_STUBS = {
    "batou-stubs": ("batou", "batou"),
    "batou_ext-stubs": ("batou_ext", "batou_ext"),
}


@dataclass(slots=True)
class StubInfo:
    """Version metadata for a stub package."""

    name: str
    version: str | None
    path: str | None
    vendored: bool = False


def _detect_stub(name: str, pkg: str, vendor_subdir: str) -> StubInfo:
    """Detect stub: prefer external package, fall back to vendored."""
    try:
        ver = metadata.version(name)
        stub_path = str(files(pkg).joinpath("lib").parent)  # type: ignore[unresolved-attribute]
        return StubInfo(name=name, version=ver, path=stub_path, vendored=False)
    except (metadata.PackageNotFoundError, AttributeError, TypeError, FileNotFoundError):
        vendor_path = VENDOR_STUBS_PATH / vendor_subdir
        if vendor_path.is_dir():
            return StubInfo(name=name, version="vendored", path=str(vendor_path), vendored=True)
        return StubInfo(name=name, version=None, path=None, vendored=False)


def _detect_all_stubs() -> list[StubInfo]:
    """Detect all stub packages with vendor fallback."""
    return [_detect_stub(name, pkg, subdir) for name, (pkg, subdir) in VENDOR_STUBS.items()]


@app.command()
def version() -> None:
    """Show version information."""
    console.print(f"batou-type [cyan]{__version__}[/]")
    for info in _detect_all_stubs():
        if info.version and info.path:
            label = "vendored" if info.vendored else info.version
            console.print(f"  [cyan]{info.name}[/] [dim]{label}[/] @ [dim]{info.path}[/]")
        else:
            console.print(f"  [yellow]{info.name}[/] [dim]<not installed>[/]")


def _run_check(
    checker: list[Checker] | None,
    paths: list[Path],
    *,
    verbose: bool = False,
    ty_args: list[str] | None = None,
) -> None:
    """Execute type checking."""
    # Show stub versions and paths
    console.print("Loaded stubs:")
    stub_infos = _detect_all_stubs()
    extra_search_paths: list[str] = []
    for info in stub_infos:
        if info.version and info.path:
            label = "vendored" if info.vendored else info.version
            console.print(f"  [cyan]{info.name}[/] [dim]{label}[/] @ [dim]{info.path}[/]")
            extra_search_paths.append(str(Path(info.path).parent.resolve()))
        else:
            console.print(f"  [yellow]{info.name}[/] [dim]<not installed>[/]")

    console.print(f"Python: [dim]{sys.executable}[/]")
    console.print()

    # Discover batou projects: direct paths + scan subdirs of non-project dirs
    projects: list[Path] = []
    for p in paths:
        if is_batou_project(p):
            projects.append(p)
        else:
            projects.extend(
                child for child in sorted(p.iterdir()) if child.is_dir() and is_batou_project(child)
            )

    if not projects:
        console.print("[yellow]No batou projects found (need components/ directory)[/]")
        raise typer.Exit(0)

    console.print(f"[green]Found {len(projects)} project(s):[/]")
    for project in projects:
        console.print(f"  [dim]{project}[/]")
    console.print()

    checkers = checker or [Checker.ty]
    failed_by_project: dict[Path, list[TypeCheckResult]] = {}

    for project in projects:
        components = find_components(project)
        if not components:
            continue

        # Detect project venv (check_all adds its site-packages to search paths)
        project_search_paths = list(extra_search_paths)
        venv = find_project_venv(project)
        if venv:
            project_search_paths.extend(venv.site_packages)
            kind = "appenv" if venv.is_appenv else "venv"
            console.print(f"[cyan]Project {kind}:[/] [dim]{venv.path}[/]")
            if verbose:
                for sp in venv.site_packages:
                    console.print(f"  [dim]{sp}[/]")
                console.print(f"[dim]PYTHONPATH: {os.pathsep.join(project_search_paths)}[/]")
            console.print()
        else:
            console.print(f"[yellow]No project venv found for {project} (checked .venv, appenv)[/]")
            console.print()

        console.print(f"[green]Checking {len(components)} component(s) in {project}...[/]")
        results = check_all(project, checkers, extra_search_paths=project_search_paths, ty_args=ty_args or [])

        for result in results:
            if result.has_errors:
                failed_by_project.setdefault(project, []).append(result)

    # Summary: error block + project lines at the bottom
    total_failed = sum(len(v) for v in failed_by_project.values())
    if failed_by_project:
        checker_names = "/".join(c.value for c in checkers)
        multi_project = len(failed_by_project) > 1
        for project, failures in failed_by_project.items():
            prefix = f"[red]{project.name}>[/] " if multi_project else ""
            for result in failures:
                if result.output.strip():
                    for line in result.output.strip().splitlines():
                        if prefix:
                            console.print(prefix, end="")
                        console.print(Text.from_ansi(line))
        console.print(f"[red]{'=' * 28} {total_failed} component(s) failed type check ({checker_names}) {'=' * 28}[/]")
    else:
        console.print("[green]All components passed type checking.[/]")

    raise typer.Exit(1 if failed_by_project else 0)


@app.command()
def check(
    paths: list[Path] = typer.Argument(
        None,
        help="Project directories to check (default: current directory)",
    ),
    checker: list[Checker] | None = typer.Option(
        None,
        "--checker",
        "-c",
        help="Type checker(s) to run (default: ty)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed debug info (PYTHONPATH, site-packages)",
    ),
    ty_args: str = typer.Option(
        "",
        "--ty-args",
        help='Extra flags passed to ty, e.g. --ty-args "--output-format concise"',
    ),
) -> None:
    """Type-check batou deployment components."""
    parsed_ty_args = shlex.split(ty_args) if ty_args else []
    _run_check(checker, paths or [Path.cwd()], verbose=verbose, ty_args=parsed_ty_args)
