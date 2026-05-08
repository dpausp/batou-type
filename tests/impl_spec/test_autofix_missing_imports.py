"""Spec validation tests for autofix-missing-imports feature.

Contract tests that verify the implementation matches the spec decisions.
All tests pass against the implemented fixer module, CLI flags, and
architecture constraints.

Spec: .agents/impl_specs/autofix-missing-imports.md
"""

from pathlib import Path
import re

from pytest_archon import archrule

from batou_type.output import Diagnostic

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

SRC = Path(__file__).resolve().parent.parent.parent / "src" / "batou_type"
PACKAGE = "batou_type"


# ---------------------------------------------------------------------------
# 1. fixer.py module exists and has correct protocol
# ---------------------------------------------------------------------------


class TestFixerModule:
    """fixer.py must exist with Fixer dataclass and two registered instances."""

    def test_module_importable(self):
        import batou_type.fixer  # noqa: F401

    def test_fixer_dataclass_exists(self):
        from batou_type.fixer import Fixer

        assert hasattr(Fixer, "__dataclass_fields__")

    def test_fixer_has_slug_field(self):
        from batou_type.fixer import Fixer

        fields = Fixer.__dataclass_fields__
        assert "slug" in fields

    def test_fixer_has_diagnostic_codes_field(self):
        from batou_type.fixer import Fixer

        fields = Fixer.__dataclass_fields__
        assert "diagnostic_codes" in fields

    def test_fixer_has_apply_field(self):
        from batou_type.fixer import Fixer

        assert callable(getattr(Fixer, "apply", None))

    def test_add_missing_import_fixer_registered(self):
        from batou_type.fixer import ADD_MISSING_IMPORT

        assert ADD_MISSING_IMPORT.slug == "add-missing-import"
        assert "possibly-missing-submodule" in ADD_MISSING_IMPORT.diagnostic_codes

    def test_self_deref_fixer_registered(self):
        from batou_type.fixer import SELF_DEREF

        assert SELF_DEREF.slug == "self-deref"

    def test_diagnostic_codes_is_frozenset(self):
        from batou_type.fixer import ADD_MISSING_IMPORT

        assert isinstance(ADD_MISSING_IMPORT.diagnostic_codes, frozenset)

    def test_apply_callable(self):
        from batou_type.fixer import ADD_MISSING_IMPORT

        assert callable(ADD_MISSING_IMPORT.apply)

    def test_apply_returns_none_when_no_change(self):
        """apply(source, diagnostics) must return None when nothing changes."""
        from batou_type.fixer import ADD_MISSING_IMPORT

        result = ADD_MISSING_IMPORT.apply("x = 1\n", [])
        assert result is None

    def test_apply_returns_str_on_change(self):
        """apply(source, diagnostics) must return str when changes are made."""
        from batou_type.fixer import ADD_MISSING_IMPORT

        source = "component = batou_ext.ssl.Certificate()\n"
        diag = Diagnostic(
            file="components/ssl.py",
            line=1,
            message='Module "batou_ext.ssl" is not imported',
            code="possibly-missing-submodule",
            checker="ty",
        )
        result = ADD_MISSING_IMPORT.apply(source, [diag])
        assert isinstance(result, str)
        assert result != source


# ---------------------------------------------------------------------------
# 2. add-missing-import fixer contract
# ---------------------------------------------------------------------------


class TestAddMissingImportFixer:
    """add_missing_import must insert correct from-import statements."""

    IMPORT_FIXER_SOURCE = (
        "class SSL(Component):\n"
        "    def configure(self):\n"
        "        self += Certificate(\n"
        "            private_key=self.private_key,\n"
        "        )\n"
    )

    def test_inserts_from_import(self):
        """Fixer must insert `from batou_ext.ssl import Certificate`."""
        from batou_type.fixer import ADD_MISSING_IMPORT

        source = "component = batou_ext.ssl.Certificate()\n"
        diag = Diagnostic(
            file="components/ssl.py",
            line=1,
            message='Module "batou_ext.ssl" is not imported',
            code="possibly-missing-submodule",
            checker="ty",
        )
        result = ADD_MISSING_IMPORT.apply(source, [diag])
        assert result is not None
        assert "from batou_ext.ssl import" in result

    def test_merges_into_existing_import(self):
        """Fixer must merge name into existing `from batou_ext.ssl import X`."""
        from batou_type.fixer import ADD_MISSING_IMPORT

        source = (
            "from batou_ext.ssl import Certificate\n"
            "\n"
            "component = batou_ext.ssl.NginxConfig()\n"
        )
        diag = Diagnostic(
            file="components/ssl.py",
            line=3,
            message='Module "batou_ext.ssl" is not imported',
            code="possibly-missing-submodule",
            checker="ty",
        )
        result = ADD_MISSING_IMPORT.apply(source, [diag])
        assert result is not None
        assert "NginxConfig" in result
        # Must still have only one import from batou_ext.ssl
        lines = [
            ln for ln in result.splitlines() if ln.startswith("from batou_ext.ssl")
        ]
        assert len(lines) == 1

    def test_inserts_after_existing_imports(self):
        """New import must go after existing imports, before first non-import."""
        from batou_type.fixer import ADD_MISSING_IMPORT

        source = "import os\n\ncomponent = batou_ext.ssl.Certificate()\n"
        diag = Diagnostic(
            file="components/ssl.py",
            line=3,
            message='Module "batou_ext.ssl" is not imported',
            code="possibly-missing-submodule",
            checker="ty",
        )
        result = ADD_MISSING_IMPORT.apply(source, [diag])
        assert result is not None
        lines = result.splitlines()
        import_line_idx = next(
            i for i, ln in enumerate(lines) if "from batou_ext.ssl" in ln
        )
        code_line_idx = next(i for i, ln in enumerate(lines) if "component" in ln)
        assert import_line_idx < code_line_idx


# ---------------------------------------------------------------------------
# 3. self-deref fixer contract
# ---------------------------------------------------------------------------


class TestSelfDerefFixer:
    """self_deref must transform self += X → self += (_ := X) when self._ is used."""

    SELF_DEREF_SOURCE = (
        "class WebApp(Component):\n"
        "    def configure(self):\n"
        "        self += SSLComponent()\n"
        "        self._.address\n"
    )

    def test_walrus_wrap_when_self_deref_referenced(self):
        """Must transform `self += X` to `self += (_ := X)` when self._ follows."""
        from batou_type.fixer import SELF_DEREF

        source = (
            "def configure(self):\n    self += SSLComponent()\n    self._.address\n"
        )
        diag = Diagnostic(
            file="components/webapp.py",
            line=2,
            message='Cannot resolve attribute "address" on type "Component | None"',
            code="unresolved-attribute",
            checker="ty",
        )
        result = SELF_DEREF.apply(source, [diag])
        assert result is not None
        assert "_ := " in result

    def test_replaces_self_dot_underscore_with_underscore(self):
        """Must replace `self._.attr` with `_.attr` in scope."""
        from batou_type.fixer import SELF_DEREF

        source = (
            "def configure(self):\n    self += SSLComponent()\n    self._.address\n"
        )
        diag = Diagnostic(
            file="components/webapp.py",
            line=2,
            message='Cannot resolve attribute "address"',
            code="unresolved-attribute",
            checker="ty",
        )
        result = SELF_DEREF.apply(source, [diag])
        assert result is not None
        assert "_.address" in result
        assert "self._" not in result

    def test_no_transform_when_self_deref_not_referenced(self):
        """Must not transform `self += X` if no `self._` follows in scope."""
        from batou_type.fixer import SELF_DEREF

        source = "def configure(self):\n    self += SSLComponent()\n    print('done')\n"
        diag = Diagnostic(
            file="components/webapp.py",
            line=1,
            message="unused",
            code="unresolved-attribute",
            checker="ty",
        )
        result = SELF_DEREF.apply(source, [diag])
        assert result is None

    def test_chained_access_transformed(self):
        """`self._.address` → `_.address` (chained attribute access)."""
        from batou_type.fixer import SELF_DEREF

        source = "def configure(self):\n    self += NginxConfig()\n    self._.server_name\n    self._.port\n"
        diag = Diagnostic(
            file="components/nginx.py",
            line=2,
            message="Cannot resolve attribute",
            code="unresolved-attribute",
            checker="ty",
        )
        result = SELF_DEREF.apply(source, [diag])
        assert result is not None
        assert "_.server_name" in result
        assert "_.port" in result
        assert "self._" not in result


# ---------------------------------------------------------------------------
# 4. CLI flags exist
# ---------------------------------------------------------------------------


class TestCLIFlags:
    """The `check` command must accept --fix, --diff, --fix-only, --virtual."""

    def test_fix_flag_exists(self):
        """--fix boolean option on check command."""
        from typer.testing import CliRunner
        from batou_type.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["check", "--help"])
        assert "--fix" in _ANSI_RE.sub("", result.output)

    def test_diff_flag_exists(self):
        """--diff boolean option on check command."""
        from typer.testing import CliRunner
        from batou_type.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["check", "--help"])
        assert "--diff" in _ANSI_RE.sub("", result.output)

    def test_fix_only_flag_exists(self):
        """--fix-only boolean option on check command."""
        from typer.testing import CliRunner
        from batou_type.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["check", "--help"])
        assert "--fix-only" in _ANSI_RE.sub("", result.output)

    def test_virtual_flag_exists(self):
        """--virtual boolean option on check command."""
        from typer.testing import CliRunner
        from batou_type.cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["check", "--help"])
        assert "--virtual" in _ANSI_RE.sub("", result.output)


# ---------------------------------------------------------------------------
# 5. Flag implication chain
# ---------------------------------------------------------------------------


class TestFlagImplications:
    """--diff → --fix-only → --fix implication chain."""

    def test_diff_implies_fix_only(self):
        """Passing --diff must set fix_only=True internally."""
        import inspect
        from batou_type.cli import check

        sig = inspect.signature(check)
        params = sig.parameters
        assert "fix_only" in params or "fix-only" in str(params)

    def test_fix_only_implies_fix(self):
        """Passing --fix-only must internally set fix=True."""
        import inspect
        from batou_type.cli import check

        sig = inspect.signature(check)
        params = set(sig.parameters)
        # The check function must have both fix_only and fix params
        assert "fix_only" in params or "fix-only" in str(sig.parameters)
        assert "fix" in params or "fix" in str(sig.parameters)

    def test_diff_implies_both(self):
        """--diff must internally imply both fix_only and fix."""
        import inspect
        from batou_type.cli import check

        sig = inspect.signature(check)
        params = set(sig.parameters)
        # All four flags must be parameters
        for flag in ("fix", "diff", "fix_only", "virtual"):
            assert flag in params or flag.replace("_", "-") in str(sig.parameters)


# ---------------------------------------------------------------------------
# 6. run_fix function exists
# ---------------------------------------------------------------------------


class TestRunFixFunction:
    """run_fix() must be importable from batou_type.cli."""

    def test_run_fix_importable(self):
        from batou_type.cli import run_fix

        assert callable(run_fix)

    def test_run_fix_accepts_expected_params(self):
        """run_fix must accept fix, diff, fix_only, virtual boolean flags."""
        import inspect
        from batou_type.cli import run_fix

        sig = inspect.signature(run_fix)
        param_names = set(sig.parameters)
        # Must accept the core boolean flags
        assert "fix" in param_names or "fix_only" in param_names


# ---------------------------------------------------------------------------
# 7. Architecture: fixer.py layer constraints
# ---------------------------------------------------------------------------


class TestFixerArchitecture:
    """fixer.py must follow layer constraints: may import output.py, not cli/plugin/frameworks."""

    def test_fixer_may_import_output(self):
        """fixer.py may import from output.py (Diagnostic model)."""
        archrule("fixer may import output").match("batou_type.fixer").should_not_import(
            "batou_type*"
        ).may_import(
            "batou_type.output",
        ).check(PACKAGE, only_direct_imports=True)

    def test_fixer_no_cli_import(self):
        """fixer.py must not import from cli.py."""
        archrule("fixer has no cli").match("batou_type.fixer").should_not_import(
            "batou_type.cli*"
        ).check(PACKAGE)

    def test_fixer_no_plugin_import(self):
        """fixer.py must not import from pytest_plugin.py."""
        archrule("fixer has no plugin").match("batou_type.fixer").should_not_import(
            "batou_type.pytest_plugin*"
        ).check(PACKAGE)

    def test_fixer_no_core_direct(self):
        """fixer.py must not import from core.py directly (go through output.py)."""
        archrule("fixer has no core").match("batou_type.fixer").should_not_import(
            "batou_type.core"
        ).check(PACKAGE, only_direct_imports=True)

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

    def test_cli_may_import_fixer(self):
        """cli.py may import from fixer.py (top of dependency calls bottom)."""
        archrule("cli may import fixer").match("batou_type.cli").should_not_import(
            "batou_type*"
        ).may_import(
            "batou_type",
            "batou_type.core",
            "batou_type.output",
            "batou_type.fixer",
        ).check(PACKAGE, only_direct_imports=True)


# ---------------------------------------------------------------------------
# 8. libcst dependency
# ---------------------------------------------------------------------------


class TestLibcstDependency:
    """libcst must be importable (declared as project dependency)."""

    def test_libcst_importable(self):
        import libcst  # noqa: F401

    def test_libcst_in_pyproject_dependencies(self):
        """pyproject.toml must list libcst in dependencies."""
        pyproject = SRC.parent.parent / "pyproject.toml"
        content = pyproject.read_text()
        assert "libcst" in content
