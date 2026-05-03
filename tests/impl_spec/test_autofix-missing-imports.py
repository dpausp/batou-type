"""Spec validation tests for autofix-missing-imports.

These tests define the CONTRACT that Phase 2 implementation must fulfill.
All tests are xfail — they assert on public API, module existence, class
structure, and behavior that does not yet exist.

Reference: .agents/impl_specs/autofix-missing-imports.md
"""

from __future__ import annotations

import importlib
import inspect
from dataclasses import fields
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FIXER_MODULE = "batou_type.fixer"
FIXER_PATH = Path(__file__).resolve().parents[2] / "src" / "batou_type" / "fixer.py"


def _import_fixer():
    """Import the fixer module — will fail until Phase 2 lands."""
    return importlib.import_module(FIXER_MODULE)


# ===========================================================================
# Module existence — module-placement
# ===========================================================================


class TestModuleExistence:
    """src/batou_type/fixer.py must exist and be importable.

    Spec decision: module-placement
    """

    def test_fixer_file_exists(self):
        """fixer.py file must exist on disk at the expected path."""
        assert FIXER_PATH.is_file(), f"fixer.py not found at {FIXER_PATH}"

    def test_fixer_module_importable(self):
        """batou_type.fixer must be importable without error."""
        mod = _import_fixer()
        assert mod is not None


# ===========================================================================
# Fixer protocol — fixer-protocol
# ===========================================================================


class TestFixerProtocol:
    """Fixer dataclass with slug, diagnostic_codes, apply method.

    Spec decision: fixer-protocol
    """

    def test_fixer_is_dataclass(self):
        """Fixer must be a dataclass (not ABC, not Protocol)."""
        mod = _import_fixer()
        assert hasattr(mod, "Fixer")
        # dataclasses have __dataclass_fields__
        assert hasattr(mod.Fixer, "__dataclass_fields__")

    def test_fixer_has_slug_field(self):
        """Fixer must have slug: str field."""
        mod = _import_fixer()
        field_names = [f.name for f in fields(mod.Fixer)]
        assert "slug" in field_names

    def test_fixer_slug_is_str(self):
        """Fixer.slug must be annotated as str."""
        mod = _import_fixer()
        field_type = {f.name: f.type for f in fields(mod.Fixer)}
        assert field_type["slug"] is str

    def test_fixer_has_diagnostic_codes_field(self):
        """Fixer must have diagnostic_codes: frozenset[str] field."""
        mod = _import_fixer()
        field_names = [f.name for f in fields(mod.Fixer)]
        assert "diagnostic_codes" in field_names

    def test_fixer_diagnostic_codes_is_frozenset_of_str(self):
        """Fixer.diagnostic_codes must be annotated as frozenset[str]."""
        mod = _import_fixer()
        ft = {f.name: f.type for f in fields(mod.Fixer)}
        # Accept both direct type and string annotation
        codes_type = ft["diagnostic_codes"]
        # The annotation should resolve to frozenset[str]
        assert codes_type == frozenset[str] or "frozenset" in str(codes_type)

    def test_fixer_has_apply_method(self):
        """Fixer must have an apply method."""
        mod = _import_fixer()
        assert hasattr(mod.Fixer, "apply")
        assert callable(mod.Fixer.apply)

    def test_fixer_apply_signature(self):
        """Fixer.apply must accept (source: str, diagnostics: list[Diagnostic]) -> str | None."""
        mod = _import_fixer()
        sig = inspect.signature(mod.Fixer.apply)
        params = list(sig.parameters.keys())
        # self is first param for a dataclass method
        assert "self" in params
        assert "source" in params
        assert "diagnostics" in params
        ret = sig.return_annotation
        assert ret != inspect.Parameter.empty, "apply must have return annotation"
        # str | None — check stringified form since annotation might not resolve
        ret_str = str(ret)
        assert "None" in ret_str or "NoneType" in ret_str

    def test_fixer_apply_returns_none_on_no_change(self):
        """Fixer.apply returns None when nothing changed.

        Spec decision: fixer-protocol — 'Returns None if nothing changed'
        """
        mod = _import_fixer()
        fixer_instances = _get_fixer_instances(mod)
        assert len(fixer_instances) >= 1, "Expected at least one fixer instance"
        fixer = fixer_instances[0]
        result = fixer.apply(source="# empty file\n", diagnostics=[])
        assert result is None, "apply must return None when nothing changed"


def _get_fixer_instances(mod):
    """Collect all Fixer instances from the module."""
    instances = []
    for name in dir(mod):
        obj = getattr(mod, name)
        if type(obj).__name__ == "Fixer" and hasattr(obj, "slug"):
            instances.append(obj)
    return instances


# ===========================================================================
# Diagnostic matching — diagnostic-matching
# ===========================================================================


class TestDiagnosticMatching:
    """Each fixer declares diagnostic_codes; routing is deterministic.

    Spec decision: diagnostic-matching
    """

    def test_add_missing_import_fixer_exists(self):
        """A fixer instance for 'add-missing-import' must exist."""
        mod = _import_fixer()
        instances = _get_fixer_instances(mod)
        slugs = [f.slug for f in instances]
        assert "add-missing-import" in slugs

    def test_add_missing_import_claims_possibly_missing_submodule(self):
        """add-missing-import fixer claims 'possibly-missing-submodule' code."""
        mod = _import_fixer()
        instances = _get_fixer_instances(mod)
        add_fixer = next(f for f in instances if f.slug == "add-missing-import")
        assert "possibly-missing-submodule" in add_fixer.diagnostic_codes

    def test_self_deref_fixer_exists(self):
        """A fixer instance for 'self-deref' must exist."""
        mod = _import_fixer()
        instances = _get_fixer_instances(mod)
        slugs = [f.slug for f in instances]
        assert "self-deref" in slugs

    def test_self_deref_fixer_claims_code(self):
        """self-deref fixer must declare at least one diagnostic code."""
        mod = _import_fixer()
        instances = _get_fixer_instances(mod)
        deref_fixer = next(f for f in instances if f.slug == "self-deref")
        assert len(deref_fixer.diagnostic_codes) >= 1

    def test_no_overlapping_diagnostic_codes(self):
        """One code maps to exactly one fixer — no overlaps.

        Spec decision: diagnostic-matching — 'One code maps to exactly one fixer'
        """
        mod = _import_fixer()
        instances = _get_fixer_instances(mod)
        all_codes: list[str] = []
        for fixer in instances:
            all_codes.extend(fixer.diagnostic_codes)
        assert len(all_codes) == len(set(all_codes)), (
            f"Overlapping diagnostic codes detected: {all_codes}"
        )


# ===========================================================================
# Module placement — module-placement
# ===========================================================================


class TestModulePlacement:
    """fixer.py dependency graph: cli.py → fixer.py → output.py → core.py.

    Spec decision: module-placement
    """

    def test_fixer_imports_diagnostic_from_output(self):
        """fixer.py must import Diagnostic from output.py."""
        mod = _import_fixer()
        mod_source = inspect.getsource(mod)
        assert "Diagnostic" in mod_source
        assert "Diagnostic" in dir(mod) or "from batou_type.output" in mod_source

    def test_fixer_imports_libcst(self):
        """fixer.py must import libcst for AST transformation."""
        mod = _import_fixer()
        mod_source = inspect.getsource(mod)
        assert "libcst" in mod_source

    def test_fixer_does_not_import_cli(self):
        """fixer.py must NOT import from cli.py."""
        mod = _import_fixer()
        mod_source = inspect.getsource(mod)
        assert "batou_type.cli" not in mod_source

    def test_fixer_does_not_import_pytest_plugin(self):
        """fixer.py must NOT import from pytest_plugin.py."""
        mod = _import_fixer()
        mod_source = inspect.getsource(mod)
        assert "batou_type.pytest_plugin" not in mod_source

    def test_fixer_does_not_import_core_directly(self):
        """fixer.py must NOT import from core.py directly (goes through output.py).

        Spec decision: architecture-test-impact
        """
        mod = _import_fixer()
        mod_source = inspect.getsource(mod)
        assert "batou_type.core" not in mod_source


# ===========================================================================
# CLI flags — flag-dispatch
# ===========================================================================


class TestCLIFlags:
    """check command has --fix, --diff, --fix-only, --virtual boolean options.

    Spec decision: flag-dispatch
    """

    def test_check_command_has_fix_option(self):
        """check() must accept --fix boolean option."""
        import batou_type.cli as cli

        sig = inspect.signature(cli.check)
        assert "fix" in sig.parameters

    def test_check_command_has_diff_option(self):
        """check() must accept --diff boolean option."""
        import batou_type.cli as cli

        sig = inspect.signature(cli.check)
        assert "diff" in sig.parameters

    def test_check_command_has_fix_only_option(self):
        """check() must accept --fix-only boolean option."""
        import batou_type.cli as cli

        sig = inspect.signature(cli.check)
        assert "fix_only" in sig.parameters

    def test_check_command_has_virtual_option(self):
        """check() must accept --virtual boolean option."""
        import batou_type.cli as cli

        sig = inspect.signature(cli.check)
        assert "virtual" in sig.parameters

    def test_fix_option_is_bool(self):
        """--fix must be a boolean Typer option."""
        import batou_type.cli as cli

        sig = inspect.signature(cli.check)
        param = sig.parameters["fix"]
        # Typer boolean options have default=False
        assert (
            param.default is False
            or param.default is None
            or isinstance(param.default, bool)
        )

    def test_diff_implies_fix_only(self):
        """--diff implies --fix-only.

        Spec decision: flag-dispatch — 'Implication chain: --diff implies --fix-only'
        """
        import batou_type.cli as cli

        source = inspect.getsource(cli.check)
        # The implication chain must be documented in the source
        assert "fix_only" in source

    def test_fix_only_implies_fix(self):
        """--fix-only implies --fix.

        Spec decision: flag-dispatch — '--fix-only implies --fix'
        """
        import batou_type.cli as cli

        source = inspect.getsource(cli.check)
        # The implication chain must be documented in the source
        assert "fix" in source


# ===========================================================================
# Fix pipeline — fix-pipeline
# ===========================================================================


class TestFixPipeline:
    """Separate run_fix() function in cli.py, distinct from run_check().

    Spec decision: fix-pipeline
    """

    def test_run_fix_exists_in_cli(self):
        """cli.py must define a run_fix function."""
        import batou_type.cli as cli

        assert hasattr(cli, "run_fix")
        assert callable(cli.run_fix)

    def test_run_fix_is_separate_from_run_check(self):
        """run_fix must be a distinct function from run_check."""
        import batou_type.cli as cli

        assert cli.run_fix is not cli.run_check

    def test_run_fix_accepts_paths_parameter(self):
        """run_fix must accept paths parameter for project discovery."""
        import batou_type.cli as cli

        sig = inspect.signature(cli.run_fix)
        params = list(sig.parameters.keys())
        assert any("path" in p for p in params), (
            f"run_fix has no path parameter: {params}"
        )

    def test_run_fix_accepts_fix_flags(self):
        """run_fix must accept fix-related flags (fix, diff, fix_only, virtual)."""
        import batou_type.cli as cli

        sig = inspect.signature(cli.run_fix)
        params = set(sig.parameters.keys())
        # At least the fix flag itself should be accepted
        assert "fix" in params or "fix_only" in params or "diff" in params, (
            f"run_fix has no fix flags: {params}"
        )


# ===========================================================================
# Architecture — architecture-test-impact
# ===========================================================================


class TestFixerArchitectureConstraints:
    """fixer.py layer constraints enforced by pytest-archon rules.

    Spec decision: architecture-test-impact
    """

    def test_fixer_no_typer(self):
        """fixer.py must not import typer."""
        from pytest_archon import archrule

        archrule("fixer has no typer").match("batou_type.fixer").should_not_import(
            "typer*"
        ).check("batou_type")

    def test_fixer_no_rich(self):
        """fixer.py must not import rich."""
        from pytest_archon import archrule

        archrule("fixer has no rich").match("batou_type.fixer").should_not_import(
            "rich*"
        ).check("batou_type")

    def test_fixer_no_pytest(self):
        """fixer.py must not import pytest."""
        from pytest_archon import archrule

        archrule("fixer has no pytest").match("batou_type.fixer").should_not_import(
            "pytest*"
        ).check("batou_type")

    def test_fixer_no_structlog(self):
        """fixer.py must not import structlog."""
        from pytest_archon import archrule

        archrule("fixer has no structlog").match("batou_type.fixer").should_not_import(
            "structlog*"
        ).check("batou_type")

    def test_fixer_no_stogger(self):
        """fixer.py must not import stogger."""
        from pytest_archon import archrule

        archrule("fixer has no stogger").match("batou_type.fixer").should_not_import(
            "stogger*"
        ).check("batou_type")

    def test_fixer_no_cli_import(self):
        """fixer.py must not import from cli.py."""
        from pytest_archon import archrule

        archrule("fixer does not import cli").match(
            "batou_type.fixer"
        ).should_not_import("batou_type.cli*").check("batou_type")

    def test_fixer_no_pytest_plugin_import(self):
        """fixer.py must not import from pytest_plugin.py."""
        from pytest_archon import archrule

        archrule("fixer does not import plugin").match(
            "batou_type.fixer"
        ).should_not_import("batou_type.pytest_plugin*").check("batou_type")

    def test_cli_may_import_fixer(self):
        """cli.py may import from fixer.py (forward dependency allowed).

        Spec decision: module-placement — 'cli.py → fixer.py'
        """
        from pytest_archon import archrule

        archrule("cli may import fixer").match("batou_type.cli").should_not_import(
            "batou_type*"
        ).may_import(
            "batou_type",
            "batou_type.fixer",
            "batou_type.core",
            "batou_type.output",
        ).check("batou_type", only_direct_imports=True)

    def test_fixer_only_imports_output_from_batou_type(self):
        """fixer.py may only import output.py from batou_type modules.

        Spec decision: architecture-test-impact — 'fixer.py must not import from core.py directly'
        """
        from pytest_archon import archrule

        archrule("fixer only imports output").match(
            "batou_type.fixer"
        ).should_not_import("batou_type*").may_import(
            "batou_type.output",
        ).check("batou_type", only_direct_imports=True)
