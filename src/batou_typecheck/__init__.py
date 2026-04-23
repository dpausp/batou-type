"""Type-check batou deployments against batou stubs."""

import json
import subprocess
import sys
from enum import Enum
from pathlib import Path
from typing import Annotated

import typer

app = typer.Typer(rich_markup_mode="none")

# Import typer echo for output
echo = typer.echo


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
    from importlib.resources import files

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
