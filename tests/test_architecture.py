"""Architecture enforcement tests for batou_type layered structure.

Layer model (top imports bottom, never reverse):

    cli.py / __main__.py    -- presentation (typer, rich)
    pytest_plugin.py        -- plugin (pytest)
    core.py                 -- domain (stdlib only)
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
        archrule("core has no typer").match("batou_type.core").should_not_import("typer*").check(PACKAGE)

    def test_core_no_rich(self):
        archrule("core has no rich").match("batou_type.core").should_not_import("rich*").check(PACKAGE)

    def test_core_no_pytest(self):
        archrule("core has no pytest").match("batou_type.core").should_not_import("pytest*").check(PACKAGE)

    def test_core_no_intra_package_imports(self):
        """core.py must not import from any other batou_type module."""
        archrule("core is self-contained").match("batou_type.core").should_not_import("batou_type*").check(PACKAGE)


# --- Framework isolation (negative checks per module) ---


class TestFrameworkIsolation:
    """Framework dependencies are isolated to their designated layer."""

    # typer: only cli.py and __main__.py may use it
    def test_core_no_typer(self):
        archrule("core: no typer").match("batou_type.core").should_not_import("typer*").check(PACKAGE)

    def test_plugin_no_typer(self):
        archrule("plugin: no typer").match("batou_type.pytest_plugin").should_not_import("typer*").check(PACKAGE)

    def test_init_no_typer(self):
        archrule("init: no typer").match("batou_type").should_not_import("typer*").check(PACKAGE, only_direct_imports=True)

    # rich: only cli.py may use it
    def test_core_no_rich(self):
        archrule("core: no rich").match("batou_type.core").should_not_import("rich*").check(PACKAGE)

    def test_plugin_no_rich(self):
        archrule("plugin: no rich").match("batou_type.pytest_plugin").should_not_import("rich*").check(PACKAGE)

    def test_init_no_rich(self):
        archrule("init: no rich").match("batou_type").should_not_import("rich*").check(PACKAGE, only_direct_imports=True)

    # pytest: only pytest_plugin.py may use it
    def test_core_no_pytest(self):
        archrule("core: no pytest").match("batou_type.core").should_not_import("pytest*").check(PACKAGE)

    def test_cli_no_pytest(self):
        archrule("cli: no pytest").match("batou_type.cli").should_not_import("pytest*").check(PACKAGE)

    def test_init_no_pytest(self):
        archrule("init: no pytest").match("batou_type").should_not_import("pytest*").check(PACKAGE, only_direct_imports=True)


# --- Cross-layer isolation ---


class TestCrossLayerIsolation:
    """CLI and plugin layers must not import each other."""

    def test_cli_no_plugin_import(self):
        archrule("CLI does not touch plugin").match("batou_type.cli").should_not_import("batou_type.pytest_plugin*").check(PACKAGE)

    def test_plugin_no_cli_import(self):
        archrule("plugin does not touch CLI").match("batou_type.pytest_plugin").should_not_import("batou_type.cli*").check(PACKAGE)

    def test_main_only_imports_cli(self):
        """__main__.py must only import from cli, nothing else in the package."""
        archrule("__main__ only uses cli").match("batou_type.__main__").should_not_import("batou_type*").may_import(
            "batou_type.cli",
        ).check(PACKAGE, only_direct_imports=True)


# --- Init purity ---


class TestInitPurity:
    """__init__.py must only re-export from core, not from cli or plugin."""

    def test_init_no_cli_import(self):
        archrule("init has no cli").match("batou_type").should_not_import("batou_type.cli*").check(PACKAGE)

    def test_init_no_plugin_import(self):
        archrule("init has no plugin").match("batou_type").should_not_import("batou_type.pytest_plugin*").check(PACKAGE)

    def test_init_only_imports_core(self):
        """__init__.py must not import from any batou_type module except core."""
        archrule("init only imports core").match("batou_type").should_not_import("batou_type*").may_import(
            "batou_type.core",
        ).check(PACKAGE, only_direct_imports=True)
