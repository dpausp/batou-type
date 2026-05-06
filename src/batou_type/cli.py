"""Batou type CLI."""

from dataclasses import dataclass
from importlib import metadata
from importlib.resources import files
from pathlib import Path
from typing import Annotated, Literal
import difflib
import re
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
    CheckerError,
    TypeCheckResult,
    check_all,
    ensure_checker_available,
    find_components,
    find_project_venv,
    is_batou_project,
)
from batou_type.fixer import ADD_MISSING_IMPORT, SELF_DEREF
from batou_type.output import Diagnostic

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


_ERROR_PATTERN = re.compile(r"\berror\b", re.IGNORECASE)


def _has_error_pattern(output: str) -> bool:
    """Check if type checker output contains error-level diagnostics."""
    return bool(_ERROR_PATTERN.search(output))


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

    log.debug(
        "project-discovery",
        input_paths=[str(p) for p in paths],
        found=len(projects),
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
        raise typer.Exit(0)

    log.info(
        "projects-found", _replace_msg="Found {count} project(s)", count=len(projects)
    )

    checkers = checker or [Checker.ty]
    log.debug("checkers-selected", checkers=[c.value for c in checkers])

    # Pre-check: verify all checkers are available before doing any work
    for c in checkers:
        try:
            ensure_checker_available(c)
        except CheckerError:
            log.exception(
                "checker-unavailable",
                _replace_msg="Type checker '{checker}' is not available",
                checker=c.value,
            )
            raise typer.Exit(2) from None
    total_failed = 0
    multi_project = len(projects) > 1
    failed_summary: dict[str, list[str]] = {}

    all_results: list[TypeCheckResult] = []

    for project in projects:
        plog = log.bind(project=str(project))
        plog.debug("project", _replace_msg="  {path}", path=str(project))
        components = find_components(project)
        if not components:
            plog.debug("project-skip-no-components")
            continue
        plog.debug("components-found", count=len(components))

        # Detect project venv (check_all adds its site-packages to search paths)
        venv = find_project_venv(project)
        if venv:
            kind = "appenv" if venv.is_appenv else "venv"
            plog.debug("project-venv", kind=kind, path=venv.path)
        else:
            plog.debug("no-venv", path=str(project))

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

        # Per-component result events — log level maps to checker output severity
        for result in results:
            component_name = Path(result.path).stem
            output = result.output.strip()
            if result.has_errors or (output and _has_error_pattern(output)):
                plog.error(
                    "component-type-errors",
                    _replace_msg="{component}: failed",
                    component=component_name,
                    stdout=output if output else None,
                )
            else:
                plog.info(
                    "component-type-passed",
                    _replace_msg="{component}: passed",
                    component=component_name,
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
            # Human mode: print error output via rich (preserves ANSI colors from ty)
            prefix = f"[red]{project.name}>[/] " if multi_project else ""
            for result in results:
                if result.has_errors and result.output.strip():
                    for line in result.output.strip().splitlines():
                        if prefix:
                            console.print(prefix, end="")
                        console.print(Text.from_ansi(line))

    # Summary events
    if total_failed:
        all_failed_names = [name for names in failed_summary.values() for name in names]
        log.warning(
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

    raise typer.Exit(1 if total_failed else 0)


def run_fix(
    paths: list[Path],
    *,
    fix: bool = False,
    diff: bool = False,
    fix_only: bool = False,
    virtual: bool = False,
    checker: list[Checker] | None = None,
    ty_args: list[str] | None = None,
) -> None:
    """Apply automated fixes for type-check diagnostics.

    Spec decision: fix-pipeline \u2014 separate function from run_check().
    Flow: (1) check_all(json_mode=True) \u2192 diagnostics, (2) group by file,
    (3) apply matching fixers, (4) write/diff/verify per flags.
    """
    log.debug(
        "fix-pipeline-start",
        paths=[str(p) for p in paths],
        fix=fix,
        diff=diff,
        fix_only=fix_only,
        virtual=virtual,
    )
    stub_infos = _detect_all_stubs()
    extra_search_paths: list[str] = []
    for info in stub_infos:
        if info.version and info.path:
            extra_search_paths.append(str(Path(info.path).parent.resolve()))

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
        raise typer.Exit(0)

    checkers = checker or [Checker.ty]
    fixers = [ADD_MISSING_IMPORT, SELF_DEREF]

    for project in projects:
        flog = log.bind(project=str(project))
        components = find_components(project)
        if not components:
            continue

        results = check_all(
            project,
            checkers,
            extra_search_paths=extra_search_paths,
            ty_args=ty_args or [],
            json_mode=True,
        )

        # Group diagnostics by file
        file_diagnostics: dict[str, list[Diagnostic]] = {}
        for result in results:
            if result.errors:
                file_diagnostics.setdefault(result.path, []).extend(result.errors)
        flog.debug(
            "fix-diagnostics-grouped",
            files=len(file_diagnostics),
            total=sum(len(d) for d in file_diagnostics.values()),
        )

        # Apply matching fixers per file
        fixed_files: list[tuple[str, str, str]] = []
        for file_path_str, diagnostics in file_diagnostics.items():
            source_path = project / file_path_str
            if not source_path.is_file():
                continue
            source = source_path.read_text()
            current = source
            for fixer in fixers:
                matched = [d for d in diagnostics if d.code in fixer.diagnostic_codes]
                if matched:
                    transformed = fixer.apply(current, matched)
                    if transformed is not None:
                        current = transformed
                        log.debug("fix-applied", file=file_path_str, fixer=fixer.slug)
            if current != source:
                fixed_files.append((file_path_str, source, current))

        # Handle output flags \u2014 diff-generation, virtual-mode-impl, fix-only-semantics
        if not fixed_files:
            flog.debug("fix-no-fixable", files=0)
            if not fix_only:
                log.info(
                    "fix-no-fixable-found",
                    _replace_msg="No fixable diagnostics found",
                    project=str(project),
                )
            raise typer.Exit(0)

        if virtual:
            # Spec decision: virtual-mode-impl — tempdir verification
            import shutil
            import tempfile

            with tempfile.TemporaryDirectory() as tmpdir:
                tmp_path = Path(tmpdir)
                for comp in components:
                    rel = comp.relative_to(project)
                    dest = tmp_path / rel
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(comp, dest)
                for name in ("pyproject.toml", ".appenv", ".venv"):
                    src = project / name
                    if src.exists():
                        if src.is_dir():
                            shutil.copytree(src, tmp_path / name)
                        else:
                            shutil.copy2(src, tmp_path / name)

                for file_path_str, _, fixed in fixed_files:
                    dest = tmp_path / file_path_str
                    dest.write_text(fixed)

                verify_results = check_all(
                    tmp_path,
                    checkers,
                    extra_search_paths=extra_search_paths,
                    ty_args=ty_args or [],
                    json_mode=True,
                )
                new_errors = sum(1 for r in verify_results if r.has_errors)
                old_errors = sum(1 for r in results if r.has_errors)
                if new_errors >= old_errors:
                    log.warning(
                        "fix-no-improvement",
                        _replace_msg="Fix did not reduce errors, skipping",
                    )
                    raise typer.Exit(1)

        if diff:
            # Spec decision: diff-generation — difflib.unified_diff
            has_diffs = False
            for file_path_str, original, fixed in fixed_files:
                diff_lines = list(
                    difflib.unified_diff(
                        original.splitlines(keepends=True),
                        fixed.splitlines(keepends=True),
                        fromfile=f"a/{file_path_str}",
                        tofile=f"b/{file_path_str}",
                    )
                )
                if diff_lines:
                    has_diffs = True
                    sys.stdout.write("".join(diff_lines))
            log.info(
                "fix-diff-summary",
                _replace_msg="{count} fixable in {projects} file(s) (run without --diff to apply)",
                count=len(fixed_files),
                projects=len(projects),
            )
            raise typer.Exit(1 if has_diffs else 0)

        # Write in-place
        if fix:
            for file_path_str, _, fixed in fixed_files:
                source_path = project / file_path_str
                source_path.write_text(fixed)
            flog.debug("fix-write-complete", files=len(fixed_files))
            log.info(
                "fix-applied-summary",
                _replace_msg="Fixed {count} file(s)",
                count=len(fixed_files),
            )
            raise typer.Exit(0)


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
    output_format: Literal["human", "json"] = typer.Option(
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
    fix: Annotated[
        bool,
        typer.Option(
            "--fix", help="Apply automated fixes for common type-check diagnostics"
        ),
    ] = False,
    diff: Annotated[
        bool,
        typer.Option(
            "--diff", help="Show unified diff of fixes instead of applying them"
        ),
    ] = False,
    fix_only: Annotated[
        bool,
        typer.Option(
            "--fix-only", help="Fix and suppress remaining error report (implies --fix)"
        ),
    ] = False,
    virtual: Annotated[
        bool,
        typer.Option(
            "--virtual", help="Verify fixes in a temporary directory before applying"
        ),
    ] = False,
) -> None:
    """Type-check batou deployment components."""
    if show_schema:
        from batou_type.output import export_schema

        import json as _json

        typer.echo(_json.dumps(export_schema(), indent=2))
        raise typer.Exit(0)

    stogger.init_logging(verbose=verbose)
    log.debug(
        "cli-invoked",
        command="check",
        paths=[str(p) for p in (paths or [Path.cwd()])],
        json_mode=json_output or output_format == "json",
        verbose=verbose,
    )
    effective_format = "json" if json_output else output_format
    json_mode = effective_format == "json"

    parsed_ty_args = shlex.split(ty_args) if ty_args else []

    # Spec decision: flag-dispatch \u2014 implication chain
    if diff:
        fix_only = True
    if fix_only:
        fix = True

    if fix:
        run_fix(
            paths or [Path.cwd()],
            fix=fix,
            diff=diff,
            fix_only=fix_only,
            virtual=virtual,
            checker=checker,
            ty_args=parsed_ty_args,
        )
        return

    run_check(
        checker,
        paths or [Path.cwd()],
        ty_args=parsed_ty_args,
        json_mode=json_mode,
    )
