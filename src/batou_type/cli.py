"""Batou type CLI."""

from dataclasses import dataclass
from importlib import metadata
from importlib.resources import files
from pathlib import Path
import shlex
import sys

import structlog
import stogger
import typer
from rich.console import Console
from rich.text import Text

from batou_type import __version__
from batou_type.core import (
    Checker,
    TypeCheckResult,
    check_all,
    find_components,
    find_project_venv,
    is_batou_project,
)

stogger.init_early_logging()
log = structlog.get_logger()

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
        stub_path = str(files(pkg).joinpath("lib").parent)  # ty: ignore[unresolved-attribute]
        return StubInfo(name=name, version=ver, path=stub_path, vendored=False)
    except (
        metadata.PackageNotFoundError,
        AttributeError,
        TypeError,
        FileNotFoundError,
    ):
        log.debug("stub-not-external", name=name)
        vendor_path = VENDOR_STUBS_PATH / vendor_subdir
        if vendor_path.is_dir():
            return StubInfo(
                name=name, version="vendored", path=str(vendor_path), vendored=True
            )
        return StubInfo(name=name, version=None, path=None, vendored=False)


def _detect_all_stubs() -> list[StubInfo]:
    """Detect all stub packages with vendor fallback."""
    return [
        _detect_stub(name, pkg, subdir) for name, (pkg, subdir) in VENDOR_STUBS.items()
    ]


@app.command()
def version() -> None:
    """Show version information."""
    console.print(f"batou-type [cyan]{__version__}[/]")
    for info in _detect_all_stubs():
        if info.version and info.path:
            label = "vendored" if info.vendored else info.version
            console.print(
                f"  [cyan]{info.name}[/] [dim]{label}[/] @ [dim]{info.path}[/]"
            )
        else:
            console.print(f"  [yellow]{info.name}[/] [dim]<not installed>[/]")


def run_check(
    checker: list[Checker] | None,
    paths: list[Path],
    *,
    ty_args: list[str] | None = None,
    json_mode: bool = False,
) -> None:
    """Execute type checking."""
    # Show stub versions and paths
    stub_infos = _detect_all_stubs()
    extra_search_paths: list[str] = []
    for info in stub_infos:
        if info.version and info.path:
            label = "vendored" if info.vendored else info.version
            log.debug("stub-info", name=info.name, version=label, path=info.path)
            extra_search_paths.append(str(Path(info.path).parent.resolve()))
        else:
            log.debug("stub-not-installed", name=info.name)

    log.debug("python-info", executable=sys.executable)

    # Discover batou projects: direct paths + scan subdirs of non-project dirs
    projects: list[Path] = []
    for p in paths:
        if is_batou_project(p):
            projects.append(p)
        else:
            projects.extend(
                child
                for child in sorted(p.iterdir())
                if child.is_dir() and is_batou_project(child)
            )

    if not projects:
        log.warning(
            "no-projects-found",
            _replace_msg="No batou projects found in {paths}",
            paths=[str(p) for p in paths],
        )
        if json_mode:
            from batou_type.output import build_output

            output = build_output(
                [], metadata={"checker": [c.value for c in (checker or [Checker.ty])]}
            )
            print(output.model_dump_json(indent=2, by_alias=True, exclude_none=True))
        else:
            console.print(
                "[yellow]No batou projects found (need components/ directory)[/]"
            )
        raise typer.Exit(0)

    log.info("projects-found", _replace_msg="Found {count} project(s)", count=len(projects))
    for project in projects:
        log.info("project", _replace_msg="  {path}", path=str(project))

    checkers = checker or [Checker.ty]
    total_failed = 0
    multi_project = len(projects) > 1
    failed_summary: dict[str, list[str]] = {}

    all_results: list[TypeCheckResult] = []

    for project in projects:
        plog = log.bind(project=str(project))
        components = find_components(project)
        if not components:
            continue

        # Detect project venv (check_all adds its site-packages to search paths)
        venv = find_project_venv(project)
        if venv:
            kind = "appenv" if venv.is_appenv else "venv"
            plog.debug("project-venv", kind=kind, path=venv.path)
        else:
            plog.debug("no-venv")

        plog.info(
            "checking-components",
            _replace_msg="Checking {count} component(s) in {project}",
            count=len(components),
        )
        results = check_all(
            project,
            checkers,
            extra_search_paths=extra_search_paths,
            ty_args=ty_args or [],
            json_mode=json_mode,
        )

        # Per-component result events
        for result in results:
            component_name = Path(result.path).stem
            status = "passed" if not result.has_errors else "failed"
            plog.info(
                "component-result",
                _replace_msg="{component}: {status}",
                component=component_name,
                status=status,
                passed=not result.has_errors,
            )

        # Collect failures for summary
        project_failed: list[str] = []
        for result in results:
            if result.has_errors:
                project_failed.append(Path(result.path).parent.name)

        total_failed += len(project_failed)
        if project_failed:
            failed_summary[str(project)] = project_failed

        all_results.extend(results)

        if not json_mode:
            # Human mode: print error output
            prefix = f"[red]{project.name}>[/] " if multi_project else ""
            for result in results:
                if result.has_errors and result.output.strip():
                    for line in result.output.strip().splitlines():
                        if prefix:
                            console.print(prefix, end="")
                        console.print(Text.from_ansi(line))

    # Summary events
    if total_failed:
        all_failed_names = [
            name for names in failed_summary.values() for name in names
        ]
        log.info(
            "components-failed",
            _replace_msg="{count} component(s) failed: {names}",
            count=total_failed,
            names=", ".join(all_failed_names),
        )
    else:
        total_count = len(all_results) or 1
        log.info(
            "components-passed",
            _replace_msg="All {count} component(s) passed",
            count=total_count,
        )

    # JSON mode: output results
    if json_mode:
        from batou_type.output import build_output

        checker_names = [c.value for c in checkers]
        output = build_output(all_results, metadata={"checker": checker_names})
        print(output.model_dump_json(indent=2, by_alias=True, exclude_none=True))
        raise typer.Exit(1 if total_failed else 0)

    # Human mode: final summary
    if total_failed:
        checker_names = "/".join(c.value for c in checkers)
        console.print(f"[red]{'=' * 46} FAILED COMPONENTS {'=' * 46}[/]")
        for project, comp_names in failed_summary.items():
            console.print(f"  [red]{project}[/]: {', '.join(comp_names)}")
        console.print(
            f"[red]{'=' * 28} {total_failed} component(s) failed type check ({checker_names}) {'=' * 28}[/]"
        )
    else:
        console.print("[green]All components passed type checking.[/]")

    raise typer.Exit(1 if total_failed else 0)


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
    output_format: str = typer.Option(
        "human",
        "--output-format",
        help="Output format: human (default) or json",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output results as JSON to stdout (shorthand for --output-format json)",
    ),
    show_schema: bool = typer.Option(
        False,
        "--show-schema",
        help="Print the JSON Schema for the output format and exit",
    ),
) -> None:
    """Type-check batou deployment components."""
    if show_schema:
        from batou_type.output import export_schema

        import json as _json

        typer.echo(_json.dumps(export_schema(), indent=2))
        raise typer.Exit(0)

    stogger.init_logging(verbose=verbose)
    effective_format = "json" if json_output else output_format
    json_mode = effective_format == "json"

    parsed_ty_args = shlex.split(ty_args) if ty_args else []
    run_check(
        checker,
        paths or [Path.cwd()],
        ty_args=parsed_ty_args,
        json_mode=json_mode,
    )
