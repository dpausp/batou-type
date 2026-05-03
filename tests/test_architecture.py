"""Architecture enforcement tests for batou_type layered structure.

Layer model (top imports bottom, never reverse):

    cli.py / __main__.py    -- presentation (typer, rich)
    pytest_plugin.py        -- plugin (pytest)
    output.py               -- output (pydantic)
    core.py                 -- domain (stdlib + lazy output import)
    vendor/                 -- isolated stubs (leaf, no upward deps)

    __init__.py re-exports from core only.

Uses pytest-archon v0.0.7 API: archrule().match().should_not_import().check(package).
"""

from pytest_archon import archrule


PACKAGE = "batou_type"


# --- Core purity: no UI/test frameworks ---


class TestCorePurity:
    """core.py must be framework-free — only stdlib allowed."""

    def test_core_no_typer(self):
        archrule("core has no typer").match("batou_type.core").should_not_import(
            "typer*"
        ).check(PACKAGE)

    def test_core_no_rich(self):
        archrule("core has no rich").match("batou_type.core").should_not_import(
            "rich*"
        ).check(PACKAGE)

    def test_core_no_pytest(self):
        archrule("core has no pytest").match("batou_type.core").should_not_import(
            "pytest*"
        ).check(PACKAGE)

    def test_core_may_import_output_only(self):
        """core.py may import from output.py for Diagnostic, but no other batou_type module."""
        archrule("core may import output").match("batou_type.core").should_not_import(
            "batou_type*"
        ).may_import(
            "batou_type.output",
        ).check(PACKAGE, only_direct_imports=True)


# --- Output layer: may import core, no frameworks ---


class TestOutputLayer:
    """output.py layer rules: may import core, must not import cli/plugin."""

    def test_output_may_import_core_only(self):
        """output.py may import from core.py, but no other batou_type module."""
        archrule("output only imports core").match(
            "batou_type.output"
        ).should_not_import("batou_type*").may_import(
            "batou_type.core",
        ).check(PACKAGE, only_direct_imports=True)

    def test_output_no_typer(self):
        archrule("output has no typer").match("batou_type.output").should_not_import(
            "typer*"
        ).check(PACKAGE)

    def test_output_no_rich(self):
        archrule("output has no rich").match("batou_type.output").should_not_import(
            "rich*"
        ).check(PACKAGE)

    def test_output_no_pytest(self):
        archrule("output has no pytest").match("batou_type.output").should_not_import(
            "pytest*"
        ).check(PACKAGE)


# --- Fixer layer: may import output only, no frameworks ---


class TestFixerLayer:
    """fixer.py layer rules: may import output.py, must not import frameworks or upper layers.

    Spec decision: architecture-test-impact
    """

    def test_fixer_no_typer(self):
        archrule("fixer has no typer").match("batou_type.fixer").should_not_import(
            "typer*"
        ).check(PACKAGE)

    def test_fixer_no_rich(self):
        archrule("fixer has no rich").match("batou_type.fixer").should_not_import(
            "rich*"
        ).check(PACKAGE)

    def test_fixer_no_pytest(self):
        archrule("fixer has no pytest").match("batou_type.fixer").should_not_import(
            "pytest*"
        ).check(PACKAGE)

    def test_fixer_no_structlog(self):
        archrule("fixer has no structlog").match("batou_type.fixer").should_not_import(
            "structlog*"
        ).check(PACKAGE)

    def test_fixer_no_stogger(self):
        archrule("fixer has no stogger").match("batou_type.fixer").should_not_import(
            "stogger*"
        ).check(PACKAGE)

    def test_fixer_no_cli_import(self):
        archrule("fixer does not import cli").match(
            "batou_type.fixer"
        ).should_not_import("batou_type.cli*").check(PACKAGE)

    def test_fixer_no_pytest_plugin_import(self):
        archrule("fixer does not import plugin").match(
            "batou_type.fixer"
        ).should_not_import("batou_type.pytest_plugin*").check(PACKAGE)

    def test_fixer_only_imports_output_from_batou_type(self):
        """fixer.py may only import output.py from batou_type modules (not core directly)."""
        archrule("fixer only imports output").match(
            "batou_type.fixer"
        ).should_not_import("batou_type*").may_import(
            "batou_type.output",
        ).check(PACKAGE, only_direct_imports=True)


# --- Framework isolation (negative checks per module) ---


class TestFrameworkIsolation:
    """Framework dependencies are isolated to their designated layer."""

    # typer: only cli.py and __main__.py may use it
    def test_core_no_typer(self):
        archrule("core: no typer").match("batou_type.core").should_not_import(
            "typer*"
        ).check(PACKAGE)

    def test_plugin_no_typer(self):
        archrule("plugin: no typer").match(
            "batou_type.pytest_plugin"
        ).should_not_import("typer*").check(PACKAGE)

    def test_init_no_typer(self):
        archrule("init: no typer").match("batou_type").should_not_import(
            "typer*"
        ).check(PACKAGE, only_direct_imports=True)

    # rich: only cli.py may use it
    def test_core_no_rich(self):
        archrule("core: no rich").match("batou_type.core").should_not_import(
            "rich*"
        ).check(PACKAGE)

    def test_plugin_no_rich(self):
        archrule("plugin: no rich").match("batou_type.pytest_plugin").should_not_import(
            "rich*"
        ).check(PACKAGE)

    def test_init_no_rich(self):
        archrule("init: no rich").match("batou_type").should_not_import("rich*").check(
            PACKAGE, only_direct_imports=True
        )

    # pytest: only pytest_plugin.py may use it
    def test_core_no_pytest(self):
        archrule("core: no pytest").match("batou_type.core").should_not_import(
            "pytest*"
        ).check(PACKAGE)

    def test_cli_no_pytest(self):
        archrule("cli: no pytest").match("batou_type.cli").should_not_import(
            "pytest*"
        ).check(PACKAGE)

    def test_init_no_pytest(self):
        archrule("init: no pytest").match("batou_type").should_not_import(
            "pytest*"
        ).check(PACKAGE, only_direct_imports=True)


# --- Cross-layer isolation ---


class TestCrossLayerIsolation:
    """CLI and plugin layers must not import each other."""

    def test_cli_no_plugin_import(self):
        archrule("CLI does not touch plugin").match("batou_type.cli").should_not_import(
            "batou_type.pytest_plugin*"
        ).check(PACKAGE)

    def test_plugin_no_cli_import(self):
        archrule("plugin does not touch CLI").match(
            "batou_type.pytest_plugin"
        ).should_not_import("batou_type.cli*").check(PACKAGE)

    def test_main_only_imports_cli(self):
        """__main__.py must only import from cli, nothing else in the package."""
        archrule("__main__ only uses cli").match(
            "batou_type.__main__"
        ).should_not_import("batou_type*").may_import(
            "batou_type.cli",
        ).check(PACKAGE, only_direct_imports=True)

    def test_cli_may_import_fixer(self):
        """cli.py may import from fixer.py, core.py, and output.py (forward dependency).

        Spec decision: module-placement — 'cli.py → fixer.py'
        """
        archrule("cli may import fixer").match("batou_type.cli").should_not_import(
            "batou_type*"
        ).may_import(
            "batou_type",
            "batou_type.fixer",
            "batou_type.core",
            "batou_type.output",
        ).check(PACKAGE, only_direct_imports=True)


# --- Init purity ---


class TestInitPurity:
    """__init__.py must only re-export from core, not from cli or plugin."""

    def test_init_no_cli_import(self):
        archrule("init has no cli").match("batou_type").should_not_import(
            "batou_type.cli*"
        ).check(PACKAGE)

    def test_init_no_plugin_import(self):
        archrule("init has no plugin").match("batou_type").should_not_import(
            "batou_type.pytest_plugin*"
        ).check(PACKAGE)

    def test_init_only_imports_core(self):
        """__init__.py must not import from any batou_type module except core."""
        archrule("init only imports core").match("batou_type").should_not_import(
            "batou_type*"
        ).may_import(
            "batou_type.core",
        ).check(PACKAGE, only_direct_imports=True)

    def test_init_no_fixer_import(self):
        archrule("init has no fixer").match("batou_type").should_not_import(
            "batou_type.fixer*"
        ).check(PACKAGE, only_direct_imports=True)
