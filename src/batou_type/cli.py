"""Batou type CLI."""

import difflib
import re
import shlex
import sys
from dataclasses import dataclass
from importlib import metadata
from importlib.resources import files
from pathlib import Path
from typing import Annotated, Any, Literal

import stogger
import structlog
import typer
from rich.console import Console
from rich.syntax import Syntax

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
from batou_type.output import CheckOutput, Diagnostic
from batou_type.setup import (
    VALID_CHECKERS,
    SetupError,
    copy_stubs,
    write_checker_config,
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


@app.callback()
def main(
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Show detailed debug info (PYTHONPATH, site-packages)",
    ),
) -> None:
    stogger.init_logging(syslog_identifier="batou-type", verbose=verbose)
    log.debug("batou-type-main", verbose=verbose, version=__version__)


@app.command()
def version() -> None:
    """Prints batou-type version and available stub packages with their locations."""
    log.info("version", _replace_msg="batou-type {version}", version=__version__)
    for info in _detect_all_stubs():
        if info.version and info.path:
            label = "vendored" if info.vendored else info.version
            log.info(
                "stub-info",
                _replace_msg="  {name} {label} @ {path}",
                name=info.name,
                label=label,
                path=info.path,
            )
        else:
            log.warning(
                "stub-not-installed",
                _replace_msg="  {name} <not installed>",
                name=info.name,
            )


_ERROR_PATTERN = re.compile(r"\berror\b", re.IGNORECASE)


def _has_error_pattern(output: str) -> bool:
    """Check if type checker output contains error-level diagnostics."""
    return bool(_ERROR_PATTERN.search(output))


def _emit_json(output: CheckOutput) -> None:
    """Emit structured JSON to stdout."""
    print(output.model_dump_json(indent=2, by_alias=True, exclude_none=True))


def _resolve_stub_paths() -> list[str]:
    """Detect all stubs and return extra search paths for type checkers."""
    stub_infos = _detect_all_stubs()
    extra_search_paths: list[str] = []
    for info in stub_infos:
        if info.version and info.path:
            label = "vendored" if info.vendored else info.version
            log.debug("stub-info", name=info.name, version=label, path=info.path)
            extra_search_paths.append(str(Path(info.path).parent.resolve()))
        else:
            log.debug("stub-not-installed", name=info.name)
    return extra_search_paths


def _discover_projects(paths: list[Path]) -> list[Path]:
    """Discover batou projects from input paths (direct or by scanning children)."""
    log.debug("discover-projects", input_count=len(paths))
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
    return projects


def _verify_checkers_available(checkers: list[Checker]) -> None:
    """Pre-check all checkers are installed. Raises typer.Exit(2) on failure."""
    for c in checkers:
        try:
            ensure_checker_available(c)
        except CheckerError:
            log.exception("checker-unavailable", checker=c.value)
            raise typer.Exit(2) from None


def _display_check_results(
    results: list[TypeCheckResult],
    checkers: list[Checker],
    project: Path,
    plog: Any,
) -> tuple[int, dict[str, list[str]]]:
    """Display per-component results and return failure counts."""
    log.debug("display-check-results", project=str(project), results=len(results))
    checker_names = ", ".join(c.value for c in checkers)
    for result in results:
        # Skip __init__.py and empty files
        if Path(result.path).name == "__init__.py":
            continue
        component_name = Path(result.path).parent.name
        file_path = project / result.path
        if not file_path.exists() or file_path.stat().st_size == 0:
            plog.debug("component-empty", component=component_name)
            continue
        output = result.output.strip()
        if result.has_errors or (output and _has_error_pattern(output)):
            plog.error(
                "component-errors",
                _replace_msg="{component} failed type check ({checkers})",
                component=component_name,
                checkers=checker_names,
                _raw_output_prefix=f"{project.name}/{component_name}",
                _raw_output=output if output else None,
            )
        else:
            plog.info(
                "component-passed",
                _replace_msg="{component} passed type check ({checkers})",
                component=component_name,
                checkers=checker_names,
            )

    # Collect failures for summary
    project_failed: list[str] = []
    for result in results:
        if result.has_errors:
            project_failed.append(Path(result.path).parent.name)

    return (
        len(project_failed),
        {str(project): project_failed} if project_failed else {},
    )


def _display_fix_preresults(
    results: list[TypeCheckResult],
    checkers: list[Checker],
    project: Path,
    flog: Any,
) -> None:
    """Show type-check results before fixing."""
    log.debug("display-fix-preresults", project=str(project), results=len(results))
    checker_names = ", ".join(c.value for c in checkers)
    for result in results:
        if Path(result.path).name == "__init__.py":
            continue
        component_name = Path(result.path).parent.name
        file_path = project / result.path
        if not file_path.exists() or file_path.stat().st_size == 0:
            continue
        output = result.output.strip()
        if result.has_errors or (output and _has_error_pattern(output)):
            flog.error(
                "component-errors",
                _replace_msg="{component} failed type check ({checkers})",
                component=component_name,
                checkers=checker_names,
                _raw_output_prefix=f"{project.name}/{component_name}",
                _raw_output=output if output else None,
            )
        else:
            flog.info(
                "component-passed",
                _replace_msg="{component} passed type check ({checkers})",
                component=component_name,
                checkers=checker_names,
            )


def _group_diagnostics_by_file(
    results: list[TypeCheckResult],
) -> dict[str, list[Diagnostic]]:
    """Group diagnostics by file path."""
    log.debug("group-diagnostics", results=len(results))
    file_diagnostics: dict[str, list[Diagnostic]] = {}
    for result in results:
        if result.errors:
            file_diagnostics.setdefault(result.path, []).extend(result.errors)
    return file_diagnostics


def _apply_fixes_to_files(
    file_diagnostics: dict[str, list[Diagnostic]],
    fixers: list[Any],
    project: Path,
) -> list[tuple[str, str, str]]:
    """Apply matching fixers per file, returning (path, original, fixed) tuples."""
    fixed: list[tuple[str, str, str]] = []
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
            fixed.append((file_path_str, source, current))
    return fixed


def _generate_diff(fixed_files: list[tuple[str, str, str]]) -> bool:
    """Generate unified diff output. Returns True if any diffs found."""
    diff_parts: list[str] = []
    for file_path_str, original, fixed in fixed_files:
        diff_text = "".join(
            difflib.unified_diff(
                original.splitlines(keepends=True),
                fixed.splitlines(keepends=True),
                fromfile=f"a/{file_path_str}",
                tofile=f"b/{file_path_str}",
            )
        )
        if diff_text:
            diff_parts.append(diff_text)
    if diff_parts:
        full_diff = "".join(diff_parts)
        syntax = Syntax(full_diff, "diff", theme="monokai")
        console.print(syntax)
    log.debug("fix-diff-summary", count=len(fixed_files))
    return bool(diff_parts)


def _verify_virtual_fix(
    projects: list[Path],
    fixed_files: list[tuple[str, str, str]],
    checkers: list[Checker],
    extra_search_paths: list[str],
    ty_args: list[str],
    all_results: list[TypeCheckResult],
) -> None:
    """Verify fixes in a temporary directory. Raises typer.Exit(1) if no improvement."""
    import shutil
    import tempfile

    for project in projects:
        components = find_components(project)
        if not components:
            continue
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
                ty_args=ty_args,
                json_mode=True,
            )
            new_errors = sum(1 for r in verify_results if r.has_errors)
            old_errors = sum(1 for r in all_results if r.has_errors)
            if new_errors >= old_errors:
                log.warning(
                    "fix-no-improvement",
                    _replace_msg="Fix did not reduce errors, skipping",
                )
                raise typer.Exit(1)


def run_check(
    checker: list[Checker] | None,
    paths: list[Path],
    *,
    ty_args: list[str] | None = None,
    json_mode: bool = False,
) -> None:
    """Execute type checking."""
    # Show stub versions and paths
    extra_search_paths = _resolve_stub_paths()

    log.debug("python-info", executable=sys.executable)

    # Discover batou projects: direct paths + scan subdirs of non-project dirs
    projects = _discover_projects(paths)

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
            _emit_json(output)
        raise typer.Exit(0)

    log.info(
        "projects-found",
        _replace_msg="Found {project_count} project(s)",
        project_count=len(projects),
    )

    checkers = checker or [Checker.ty]
    log.debug("checkers-selected", checkers=[c.value for c in checkers])

    # Pre-check: verify all checkers are available before doing any work
    _verify_checkers_available(checkers)

    total_failed = 0
    failed_summary: dict[str, list[str]] = {}

    all_results: list[TypeCheckResult] = []

    for project in projects:
        plog = log.bind(project=str(project))
        plog.debug("project", _replace_msg="  {path}", path=str(project))
        components = find_components(project)
        if not components:
            plog.debug("project-skip-no-components")
            continue
        plog.debug("components-found", component_count=len(components))

        # Detect project venv (check_all adds its site-packages to search paths)
        venv = find_project_venv(project)
        if venv:
            kind = "appenv" if venv.is_appenv else "venv"
            plog.debug("project-venv", kind=kind, path=venv.path)
        else:
            plog.debug("no-venv", path=str(project))

        plog.info(
            "checking-components",
            _replace_msg="Checking {component_count} component(s) in {project}",
            component_count=len(components),
        )
        plog.debug(
            "check-all-start",
            checkers=[c.value for c in checkers],
            extra_search_paths=extra_search_paths,
        )
        results = check_all(
            project,
            checkers,
            extra_search_paths=extra_search_paths,
            ty_args=ty_args or [],
            json_mode=json_mode,
        )

        # Per-component result events — log level maps to checker output severity
        project_failed_count, project_failures = _display_check_results(
            results, checkers, project, plog
        )
        total_failed += project_failed_count
        failed_summary.update(project_failures)

        all_results.extend(results)

    # Summary events
    if total_failed:
        all_failed_names = [name for names in failed_summary.values() for name in names]
        log.warning(
            "components-failed",
            _replace_msg="{failed_count} component(s) failed: {names}",
            failed_count=total_failed,
            names=", ".join(all_failed_names),
        )
    else:
        total_count = len(all_results) or 1
        log.info(
            "components-passed",
            _replace_msg="All {passed_count} component(s) passed",
            passed_count=total_count,
        )

    # JSON mode: output results
    if json_mode:
        from batou_type.output import build_output

        checker_names = [c.value for c in checkers]
        output = build_output(all_results, metadata={"checker": checker_names})
        _emit_json(output)
        raise typer.Exit(1 if total_failed else 0)

    # Human mode: final summary
    if total_failed:
        checker_names = "/".join(c.value for c in checkers)
        log.error("components-failed-header", _replace_msg="  FAILED COMPONENTS")
        for project, comp_names in failed_summary.items():
            log.error(
                "components-failed-project",
                _replace_msg="  {project}: {names}",
                project=project,
                names=", ".join(comp_names),
            )
        log.error(
            "components-failed-summary",
            _replace_msg="  {total_failed} component(s) failed type check ({checkers})",
            total_failed=total_failed,
            checkers=checker_names,
        )

    raise typer.Exit(1 if total_failed else 0)


def run_fix(
    paths: list[Path],
    *,
    fix: bool = False,
    diff: bool = False,
    fix_only: bool = False,
    virtual: bool = False,
    json_mode: bool = False,
    checker: list[Checker] | None = None,
    ty_args: list[str] | None = None,
) -> None:
    """Apply automated fixes for type-check diagnostics.

    Spec decision: fix-pipeline — separate function from run_check().
    Flow: (1) check_all(json_mode=True) → diagnostics, (2) group by file,
    (3) apply matching fixers, (4) write/diff/verify per flags.
    """
    log.debug(
        "fix-pipeline-start",
        paths=[str(p) for p in paths],
        fix=fix,
        diff=diff,
        fix_only=fix_only,
    )
    extra_search_paths = _resolve_stub_paths()

    projects = _discover_projects(paths)

    if not projects:
        log.warning(
            "no-projects-found",
            _replace_msg="No batou projects found in {paths}",
            paths=[str(p) for p in paths],
        )
        raise typer.Exit(0)

    checkers = checker or [Checker.ty]
    fixers = [ADD_MISSING_IMPORT, SELF_DEREF]
    log.debug("fix-fixers", fixers=[f.slug for f in fixers])

    all_results: list[TypeCheckResult] = []
    all_fixed_files: list[tuple[str, str, str]] = []

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

        # Show type-check results before fixing (unless fix_only or json_mode)
        if not fix_only and not json_mode:
            _display_fix_preresults(results, checkers, project, flog)

        # Group diagnostics by file
        file_diagnostics = _group_diagnostics_by_file(results)
        flog.debug(
            "fix-diagnostics-grouped",
            files=len(file_diagnostics),
            total=sum(len(d) for d in file_diagnostics.values()),
        )

        # Apply matching fixers per file
        project_fixed = _apply_fixes_to_files(file_diagnostics, fixers, project)
        all_fixed_files.extend(project_fixed)

        all_results.extend(results)
        flog.debug("fix-files-changed", count=len(all_fixed_files))

    # Handle output flags — diff-generation, virtual-mode-impl, fix-only-semantics
    if not all_fixed_files:
        flog.debug("fix-no-fixable", files=0)
        if not fix_only:
            log.info(
                "fix-no-fixable-found",
                _replace_msg="No fixable diagnostics found",
            )
        if json_mode:
            from batou_type.output import build_output

            output = build_output(
                all_results,
                metadata={"checker": [c.value for c in checkers]},
            )
            _emit_json(output)
        raise typer.Exit(0)

    if virtual:
        _verify_virtual_fix(
            projects,
            all_fixed_files,
            checkers,
            extra_search_paths,
            ty_args or [],
            all_results,
        )

    if diff:
        # Spec decision: diff-generation — Rich-colored unified diff
        has_diffs = _generate_diff(all_fixed_files)
        log.info(
            "fix-diff-summary",
            _replace_msg="{count} fixable file(s) (run without --diff to apply)",
            count=len(all_fixed_files),
        )
        raise typer.Exit(1 if has_diffs else 0)

    # Write in-place
    if fix:
        for project in projects:
            for file_path_str, _, fixed in all_fixed_files:
                source_path = project / file_path_str
                source_path.write_text(fixed)
        flog.debug("fix-write-complete", files=len(all_fixed_files))
        log.info(
            "fix-applied-summary",
            _replace_msg="Fixed {count} file(s)",
            count=len(all_fixed_files),
        )

    # JSON mode: output results
    if json_mode:
        from batou_type.output import build_output

        checker_names = [c.value for c in checkers]
        output = build_output(
            all_results,
            metadata={"checker": checker_names},
        )
        _emit_json(output)

    raise typer.Exit(0)


@app.command()
def check(
    paths: Annotated[
        list[Path] | None,
        typer.Argument(
            help="Project directories to check (default: current directory)",
        ),
    ] = None,
    checker: Annotated[
        list[Checker] | None,
        typer.Option(
            "--checker",
            "-c",
            help="Type checker(s) to run (default: ty)",
        ),
    ] = None,
    ty_args: Annotated[
        str,
        typer.Option(
            "--ty-args",
            help='Extra flags passed to ty, e.g. --ty-args "--output-format concise"',
        ),
    ] = "",
    output_format: Annotated[
        Literal["human", "json"],
        typer.Option(
            "--output-format",
            help="Output format: human (default) or json",
        ),
    ] = "human",
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Output results as JSON to stdout (shorthand for --output-format json)",
        ),
    ] = False,
    show_schema: Annotated[
        bool,
        typer.Option(
            "--show-schema",
            help="Print the JSON Schema for the output format and exit",
        ),
    ] = False,
    fix: Annotated[
        bool,
        typer.Option(
            "--fix", help="Automatically fixes common type-check errors in-place"
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
            "--fix-only",
            help="Fixes what it can, skips the error summary (implies --fix)",
        ),
    ] = False,
    virtual: Annotated[
        bool,
        typer.Option(
            "--virtual", help="Verify fixes in a temporary directory before applying"
        ),
    ] = False,
) -> None:
    """Type-check batou deployment components against bundled stubs."""
    if show_schema:
        import json as _json

        from batou_type.output import export_schema

        typer.echo(_json.dumps(export_schema(), indent=2))
        raise typer.Exit(0)

    log.debug(
        "cli-invoked",
        command="check",
        paths=[str(p) for p in (paths or [Path.cwd()])],
        json_mode=json_output or output_format == "json",
    )
    effective_format = "json" if json_output else output_format
    json_mode = effective_format == "json"
    log.debug("check-mode", json_mode=json_mode, fix=fix, diff=diff, fix_only=fix_only)

    parsed_ty_args = shlex.split(ty_args) if ty_args else []

    # Spec decision: flag-dispatch — implication chain
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
            json_mode=json_mode,
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


@app.command()
def setup(
    path: Annotated[
        Path | None,
        typer.Argument(
            help="Sets up type checking in this batou project (default: current directory)"
        ),
    ] = None,
    checkers: Annotated[
        str | None,
        typer.Option(
            help="Installs stubs and config for these checkers (default: all supported)"
        ),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Shows what would change without writing files"),
    ] = False,
) -> None:
    """Sets up pyproject.toml and stubs for IDE-native type checking of batou components."""
    target = (path or Path.cwd()).resolve()
    log.debug("setup-target", target=str(target))

    if not is_batou_project(target):
        log.error(
            "not-a-batou-project",
            _replace_msg="Not a batou project: {target}",
            target=target,
        )
        raise typer.Exit(code=1)

    selected = VALID_CHECKERS
    log.debug("setup-checkers", selected=selected)
    if checkers:
        selected = [c.strip() for c in checkers.split(",")]
        invalid = [c for c in selected if c not in VALID_CHECKERS]
        if invalid:
            log.error(
                "unknown-checkers",
                _replace_msg="Unknown checkers: {checkers}",
                checkers=", ".join(invalid),
            )
            raise typer.Exit(code=1)

    try:
        write_checker_config(target, selected, dry_run=dry_run)
    except SetupError as exc:
        log.exception(
            "setup-conflict",
            sections=", ".join(exc.conflicting_sections),
        )
        raise typer.Exit(code=1)

    if not dry_run:
        copy_stubs(target, VENDOR_STUBS_PATH)
        log.info("setup-complete", _replace_msg="Setup complete.")
    else:
        log.info("setup-dry-run", _replace_msg="Dry run — no files written.")
