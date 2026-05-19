"""Architecture enforcement tests for batou_type layered structure.

Layer model (top imports bottom, never reverse):

    cli.py / __main__.py    -- presentation (typer, rich, stogger)
    fixer.py                -- autofix transforms (libcst)
    pytest_plugin.py        -- plugin (pytest)
    output.py               -- output (pydantic)
    core.py                 -- domain (stdlib + lazy output import)

    __init__.py re-exports from core only.

Uses pytest-archon v0.0.7 API: archrule().match().should_not_import().check(package).
"""

from pathlib import Path

from pytest_archon import archrule


PACKAGE = "batou_type"


# --- Core purity: no UI/test frameworks ---


def test_core_no_typer() -> None:
    archrule("core has no typer").match("batou_type.core").should_not_import(
        "typer*"
    ).check(PACKAGE)


def test_core_no_rich() -> None:
    archrule("core has no rich").match("batou_type.core").should_not_import(
        "rich*"
    ).check(PACKAGE)


def test_core_no_pytest() -> None:
    archrule("core has no pytest").match("batou_type.core").should_not_import(
        "pytest*"
    ).check(PACKAGE)


def test_core_may_import_output_only() -> None:
    """core.py may import from output.py for Diagnostic, but no other batou_type module."""
    archrule("core may import output").match("batou_type.core").should_not_import(
        "batou_type*"
    ).may_import(
        "batou_type.output",
    ).check(PACKAGE, only_direct_imports=True)


# --- Output layer: may import core, no frameworks ---


def test_output_may_import_core_only() -> None:
    """output.py may import from core.py, but no other batou_type module."""
    archrule("output only imports core").match("batou_type.output").should_not_import(
        "batou_type*"
    ).may_import(
        "batou_type.core",
    ).check(PACKAGE, only_direct_imports=True)


def test_output_no_typer() -> None:
    archrule("output has no typer").match("batou_type.output").should_not_import(
        "typer*"
    ).check(PACKAGE)


def test_output_no_rich() -> None:
    archrule("output has no rich").match("batou_type.output").should_not_import(
        "rich*"
    ).check(PACKAGE)


def test_output_no_pytest() -> None:
    archrule("output has no pytest").match("batou_type.output").should_not_import(
        "pytest*"
    ).check(PACKAGE)


# --- Fixer layer: may import output only, no frameworks ---


def test_fixer_no_typer() -> None:
    archrule("fixer has no typer").match("batou_type.fixer").should_not_import(
        "typer*"
    ).check(PACKAGE)


def test_fixer_no_rich() -> None:
    archrule("fixer has no rich").match("batou_type.fixer").should_not_import(
        "rich*"
    ).check(PACKAGE)


def test_fixer_no_pytest() -> None:
    archrule("fixer has no pytest").match("batou_type.fixer").should_not_import(
        "pytest*"
    ).check(PACKAGE)


def test_fixer_no_structlog() -> None:
    archrule("fixer has no structlog").match("batou_type.fixer").should_not_import(
        "structlog*"
    ).check(PACKAGE)


def test_fixer_no_stogger() -> None:
    archrule("fixer has no stogger").match("batou_type.fixer").should_not_import(
        "stogger*"
    ).check(PACKAGE)


def test_fixer_no_cli_import() -> None:
    archrule("fixer does not import cli").match("batou_type.fixer").should_not_import(
        "batou_type.cli*"
    ).check(PACKAGE)


def test_fixer_no_pytest_plugin_import() -> None:
    archrule("fixer does not import plugin").match(
        "batou_type.fixer"
    ).should_not_import("batou_type.pytest_plugin*").check(PACKAGE)


def test_fixer_only_imports_output_from_batou_type() -> None:
    """fixer.py may only import output.py from batou_type modules (not core directly)."""
    archrule("fixer only imports output").match("batou_type.fixer").should_not_import(
        "batou_type*"
    ).may_import(
        "batou_type.output",
    ).check(PACKAGE, only_direct_imports=True)


# --- Framework isolation (negative checks per module) ---


# typer: only cli.py and __main__.py may use it
def test_framework_isolation_core_no_typer() -> None:
    archrule("core: no typer").match("batou_type.core").should_not_import(
        "typer*"
    ).check(PACKAGE)


def test_framework_isolation_plugin_no_typer() -> None:
    archrule("plugin: no typer").match("batou_type.pytest_plugin").should_not_import(
        "typer*"
    ).check(PACKAGE)


def test_framework_isolation_init_no_typer() -> None:
    archrule("init: no typer").match("batou_type").should_not_import("typer*").check(
        PACKAGE, only_direct_imports=True
    )


# rich: only cli.py may use it
def test_framework_isolation_core_no_rich() -> None:
    archrule("core: no rich").match("batou_type.core").should_not_import("rich*").check(
        PACKAGE
    )


def test_framework_isolation_plugin_no_rich() -> None:
    archrule("plugin: no rich").match("batou_type.pytest_plugin").should_not_import(
        "rich*"
    ).check(PACKAGE)


def test_framework_isolation_init_no_rich() -> None:
    archrule("init: no rich").match("batou_type").should_not_import("rich*").check(
        PACKAGE, only_direct_imports=True
    )


# pytest: only pytest_plugin.py may use it
def test_framework_isolation_core_no_pytest() -> None:
    archrule("core: no pytest").match("batou_type.core").should_not_import(
        "pytest*"
    ).check(PACKAGE)


def test_framework_isolation_cli_no_pytest() -> None:
    archrule("cli: no pytest").match("batou_type.cli").should_not_import(
        "pytest*"
    ).check(PACKAGE)


def test_framework_isolation_init_no_pytest() -> None:
    archrule("init: no pytest").match("batou_type").should_not_import("pytest*").check(
        PACKAGE, only_direct_imports=True
    )


# --- Cross-layer isolation ---


def test_cli_no_plugin_import() -> None:
    archrule("CLI does not touch plugin").match("batou_type.cli").should_not_import(
        "batou_type.pytest_plugin*"
    ).check(PACKAGE)


def test_plugin_no_cli_import() -> None:
    archrule("plugin does not touch CLI").match(
        "batou_type.pytest_plugin"
    ).should_not_import("batou_type.cli*").check(PACKAGE)


def test_main_only_imports_cli() -> None:
    """__main__.py must only import from cli, nothing else in the package."""
    archrule("__main__ only uses cli").match("batou_type.__main__").should_not_import(
        "batou_type*"
    ).may_import(
        "batou_type.cli",
    ).check(PACKAGE, only_direct_imports=True)


def test_cli_may_import_fixer() -> None:
    """cli.py may import from fixer.py, core.py, output.py, and setup.py (forward dependency).

    Spec decision: module-placement — 'cli.py → fixer.py', 'cli.py → setup.py'
    """
    archrule("cli may import fixer").match("batou_type.cli").should_not_import(
        "batou_type*"
    ).may_import(
        "batou_type",
        "batou_type.fixer",
        "batou_type.core",
        "batou_type.output",
        "batou_type.setup",
    ).check(PACKAGE, only_direct_imports=True)


# --- Init purity ---


def test_init_no_cli_import() -> None:
    archrule("init has no cli").match("batou_type").should_not_import(
        "batou_type.cli*"
    ).check(PACKAGE)


def test_init_no_plugin_import() -> None:
    archrule("init has no plugin").match("batou_type").should_not_import(
        "batou_type.pytest_plugin*"
    ).check(PACKAGE)


def test_init_only_imports_core() -> None:
    """__init__.py must not import from any batou_type module except core."""
    archrule("init only imports core").match("batou_type").should_not_import(
        "batou_type*"
    ).may_import(
        "batou_type.core",
    ).check(PACKAGE, only_direct_imports=True)


def test_init_no_fixer_import() -> None:
    archrule("init has no fixer").match("batou_type").should_not_import(
        "batou_type.fixer*"
    ).check(PACKAGE, only_direct_imports=True)


# --- setup.py layer: stdlib + structlog only ---


def test_setup_module_importable() -> None:
    import importlib

    importlib.import_module("batou_type.setup")


def test_setup_no_typer() -> None:
    archrule("setup has no typer").match("batou_type.setup").should_not_import(
        "typer*"
    ).check(PACKAGE)


def test_setup_no_rich() -> None:
    archrule("setup has no rich").match("batou_type.setup").should_not_import(
        "rich*"
    ).check(PACKAGE)


def test_setup_no_pytest() -> None:
    archrule("setup has no pytest").match("batou_type.setup").should_not_import(
        "pytest*"
    ).check(PACKAGE)


def test_setup_no_pydantic() -> None:
    archrule("setup has no pydantic").match("batou_type.setup").should_not_import(
        "pydantic*"
    ).check(PACKAGE)


def test_setup_no_libcst() -> None:
    archrule("setup has no libcst").match("batou_type.setup").should_not_import(
        "libcst*"
    ).check(PACKAGE)


def test_setup_no_stogger() -> None:
    archrule("setup has no stogger").match("batou_type.setup").should_not_import(
        "stogger*"
    ).check(PACKAGE)


def test_setup_no_batou_type_imports() -> None:
    """setup.py must not import any batou_type module (stdlib + structlog only)."""
    archrule("setup: no batou_type imports").match(
        "batou_type.setup"
    ).should_not_import("batou_type*").check(PACKAGE, only_direct_imports=True)


# --- Dependency availability ---


def test_libcst_importable() -> None:
    import libcst  # noqa: F401


def test_libcst_in_pyproject_dependencies() -> None:
    """pyproject.toml must list libcst in dependencies."""
    pyproject = Path(__file__).resolve().parent.parent.parent / "pyproject.toml"
    content = pyproject.read_text()
    assert "libcst" in content
