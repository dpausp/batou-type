"""Spec validation tests for the setup subcommand.

Contract tests that verify the implementation matches the spec decisions in
setup-command.md.

Spec: .agents/impl_specs/setup-command.md
"""

import re
import subprocess
import sys
from pathlib import Path

import pytest
from pytest_archon import archrule

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

PACKAGE = "batou_type"
BATOU_TYPE_CLI = [sys.executable, "-m", "batou_type"]
VENDOR = Path(__file__).resolve().parent.parent.parent / "src" / "batou_type" / "vendor"


def _strip_ansi(text: str) -> str:
    return ANSI_RE.sub("", text)


def run_cli(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Run batou-type CLI and return result."""
    import os

    env = os.environ.copy()
    env.pop("JOURNAL_STREAM", None)
    return subprocess.run(
        [*BATOU_TYPE_CLI, *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        env=env,
    )


@pytest.fixture
def batou_project(tmp_path: Path) -> Path:
    """Create a minimal batou project with components/ directory."""
    (tmp_path / "components").mkdir()
    return tmp_path


# ---------------------------------------------------------------------------
# 1. Module Architecture — setup.py constraints
# ---------------------------------------------------------------------------


class TestSetupModuleArchitecture:
    """setup.py must exist with stdlib+structlog-only imports, no batou_type imports."""

    def test_setup_module_exists(self) -> None:
        """setup.py exists and is importable."""
        import importlib

        importlib.import_module("batou_type.setup")

    def test_setup_no_typer(self) -> None:
        archrule("setup has no typer").match("batou_type.setup").should_not_import(
            "typer*"
        ).check(PACKAGE)

    def test_setup_no_rich(self) -> None:
        archrule("setup has no rich").match("batou_type.setup").should_not_import(
            "rich*"
        ).check(PACKAGE)

    def test_setup_no_pytest(self) -> None:
        archrule("setup has no pytest").match("batou_type.setup").should_not_import(
            "pytest*"
        ).check(PACKAGE)

    def test_setup_no_pydantic(self) -> None:
        archrule("setup has no pydantic").match("batou_type.setup").should_not_import(
            "pydantic*"
        ).check(PACKAGE)

    def test_setup_no_libcst(self) -> None:
        archrule("setup has no libcst").match("batou_type.setup").should_not_import(
            "libcst*"
        ).check(PACKAGE)

    def test_setup_no_stogger(self) -> None:
        archrule("setup has no stogger").match("batou_type.setup").should_not_import(
            "stogger*"
        ).check(PACKAGE)

    def test_setup_no_batou_type_imports(self) -> None:
        """setup.py must not import any batou_type module (stdlib + structlog only)."""
        archrule("setup: no batou_type imports").match(
            "batou_type.setup"
        ).should_not_import("batou_type*").check(PACKAGE, only_direct_imports=True)

    def test_cli_may_import_setup(self) -> None:
        """cli.py may import from setup.py (forward dependency per spec)."""
        import importlib

        importlib.import_module("batou_type.setup")
        archrule("cli may import setup").match("batou_type.cli").should_not_import(
            "batou_type*"
        ).may_import(
            "batou_type",
            "batou_type.setup",
            "batou_type.fixer",
            "batou_type.core",
            "batou_type.output",
        ).check(PACKAGE, only_direct_imports=True)


# ---------------------------------------------------------------------------
# 2. CLI Registration
# ---------------------------------------------------------------------------


class TestSetupCLIRegistration:
    """CLI registration of the setup subcommand."""

    def test_setup_help_exits_zero(self) -> None:
        """batou-type setup --help exits 0."""
        result = run_cli("setup", "--help")
        assert result.returncode == 0

    def test_setup_help_shows_description(self) -> None:
        """batou-type setup --help shows 'IDE-native type checking' in description."""
        result = run_cli("setup", "--help")
        output = _strip_ansi(result.stdout.lower())
        assert "ide-native type checking" in output

    def test_setup_help_shows_options(self) -> None:
        """batou-type setup --help shows --checkers and --dry-run options."""
        result = run_cli("setup", "--help")
        output = _strip_ansi(result.stdout.lower())
        assert "--checkers" in output
        assert "--dry-run" in output

    def test_root_help_lists_setup(self) -> None:
        """batou-type --help lists 'setup' as a subcommand."""
        result = run_cli("--help")
        assert result.returncode == 0
        output = _strip_ansi(result.stdout.lower())
        assert "setup" in output

    def test_setup_non_project_path_exits_one(self, tmp_path: Path) -> None:
        """batou-type setup with non-project path exits 1 with 'Not a batou project'."""
        result = run_cli("setup", str(tmp_path))
        assert result.returncode == 1
        output = (result.stdout + result.stderr).lower()
        assert "not a batou project" in output

    def test_setup_dry_run_exits_zero(self, batou_project: Path) -> None:
        """batou-type setup --dry-run exits 0 without writing files."""
        result = run_cli("setup", "--dry-run", str(batou_project))
        assert result.returncode == 0
        # --dry-run must not create stubs/ or pyproject.toml
        assert not (batou_project / "stubs").exists()
        assert not (batou_project / "pyproject.toml").exists()

    def test_setup_checkers_ty_only(self, batou_project: Path) -> None:
        """batou-type setup --checkers ty only writes ty config, not mypy/pyright."""
        result = run_cli("setup", "--checkers", "ty", str(batou_project))
        assert result.returncode == 0
        content = (batou_project / "pyproject.toml").read_text()
        assert "[tool.ty.environment]" in content
        assert "[tool.mypy]" not in content
        assert "[tool.pyright]" not in content


# ---------------------------------------------------------------------------
# 3. Stub Copying
# ---------------------------------------------------------------------------


class TestStubCopying:
    """Stubs are copied from vendor/ into target project as PEP 561 packages."""

    def test_stubs_batou_dir_created(self, batou_project: Path) -> None:
        """After setup, stubs/batou/ directory exists."""
        run_cli("setup", str(batou_project))
        assert (batou_project / "stubs" / "batou").is_dir()

    def test_stubs_batou_ext_dir_created(self, batou_project: Path) -> None:
        """After setup, stubs/batou_ext/ directory exists."""
        run_cli("setup", str(batou_project))
        assert (batou_project / "stubs" / "batou_ext").is_dir()

    def test_stubs_contain_pyi_files(self, batou_project: Path) -> None:
        """Copied stubs contain .pyi files (PEP 561 structure)."""
        run_cli("setup", str(batou_project))
        batou_pyi = list((batou_project / "stubs" / "batou").rglob("*.pyi"))
        batou_ext_pyi = list((batou_project / "stubs" / "batou_ext").rglob("*.pyi"))
        assert len(batou_pyi) > 0, "stubs/batou/ must contain .pyi files"
        assert len(batou_ext_pyi) > 0, "stubs/batou_ext/ must contain .pyi files"

    def test_stubs_have_py_typed_markers(self, batou_project: Path) -> None:
        """Copied stub packages include py.typed markers."""
        run_cli("setup", str(batou_project))
        assert (batou_project / "stubs" / "batou" / "py.typed").exists()
        assert (batou_project / "stubs" / "batou_ext" / "py.typed").exists()

    def test_stub_content_matches_vendor(self, batou_project: Path) -> None:
        """Stub content matches vendored originals exactly."""
        run_cli("setup", str(batou_project))
        # Check batou/__init__.pyi
        vendor_init = VENDOR / "batou" / "__init__.pyi"
        copied_init = batou_project / "stubs" / "batou" / "__init__.pyi"
        assert vendor_init.read_text() == copied_init.read_text()
        # Check batou_ext/__init__.pyi
        vendor_ext_init = VENDOR / "batou_ext" / "__init__.pyi"
        copied_ext_init = batou_project / "stubs" / "batou_ext" / "__init__.pyi"
        assert vendor_ext_init.read_text() == copied_ext_init.read_text()


# ---------------------------------------------------------------------------
# 4. pyproject.toml Writing
# ---------------------------------------------------------------------------


class TestPyprojectWriting:
    """Checker configuration is written to pyproject.toml."""

    def test_creates_pyproject_if_missing(self, batou_project: Path) -> None:
        """Creates pyproject.toml with [project] header when missing."""
        run_cli("setup", str(batou_project))
        toml = (batou_project / "pyproject.toml").read_text()
        assert "[project]" in toml

    def test_new_pyproject_has_name_and_version(self, batou_project: Path) -> None:
        """New pyproject.toml has name (from directory) and version."""
        run_cli("setup", str(batou_project))
        toml = (batou_project / "pyproject.toml").read_text()
        assert 'version = "0.1.0"' in toml
        assert "name" in toml

    def test_writes_tool_ty_section(self, batou_project: Path) -> None:
        """Writes [tool.ty.environment] with extra-paths."""
        run_cli("setup", str(batou_project))
        toml = (batou_project / "pyproject.toml").read_text()
        assert "[tool.ty.environment]" in toml
        assert 'extra-paths = ["stubs"]' in toml

    def test_writes_tool_ty_src_section(self, batou_project: Path) -> None:
        """Writes [tool.ty.src] with include = ["components"]."""
        run_cli("setup", str(batou_project))
        toml = (batou_project / "pyproject.toml").read_text()
        assert "[tool.ty.src]" in toml
        assert 'include = ["components"]' in toml

    def test_writes_tool_mypy_section(self, batou_project: Path) -> None:
        """Writes [tool.mypy] with required keys."""
        run_cli("setup", str(batou_project))
        toml = (batou_project / "pyproject.toml").read_text()
        assert "[tool.mypy]" in toml
        assert 'mypy_path = "stubs"' in toml
        assert "explicit_package_bases = true" in toml
        assert "check_untyped_defs = true" in toml
        assert 'modules = ["components"]' in toml

    def test_writes_tool_pyright_section(self, batou_project: Path) -> None:
        """Writes [tool.pyright] with include and stubPath."""
        run_cli("setup", str(batou_project))
        toml = (batou_project / "pyproject.toml").read_text()
        assert "[tool.pyright]" in toml
        assert 'include = ["components"]' in toml
        assert 'stubPath = "stubs"' in toml

    def test_managed_marker_present(self, batou_project: Path) -> None:
        """Comment marker '# managed by batou-type setup' on managed sections."""
        run_cli("setup", str(batou_project))
        toml = (batou_project / "pyproject.toml").read_text()
        assert "# managed by batou-type setup" in toml


# ---------------------------------------------------------------------------
# 5. Idempotency
# ---------------------------------------------------------------------------


class TestIdempotency:
    """Second setup run succeeds and produces identical output."""

    def test_second_run_succeeds(self, batou_project: Path) -> None:
        """Second batou-type setup run exits 0."""
        run_cli("setup", str(batou_project))
        result = run_cli("setup", str(batou_project))
        assert result.returncode == 0

    def test_second_run_preserves_config(self, batou_project: Path) -> None:
        """Second run produces the same pyproject.toml content."""
        run_cli("setup", str(batou_project))
        first = (batou_project / "pyproject.toml").read_text()
        run_cli("setup", str(batou_project))
        second = (batou_project / "pyproject.toml").read_text()
        assert first == second

    def test_second_run_preserves_stubs(self, batou_project: Path) -> None:
        """Second run produces identical stub file tree."""
        result = run_cli("setup", str(batou_project))
        assert result.returncode == 0
        first_files = sorted(
            str(p.relative_to(batou_project))
            for p in (batou_project / "stubs").rglob("*")
            if p.is_file()
        )
        run_cli("setup", str(batou_project))
        second_files = sorted(
            str(p.relative_to(batou_project))
            for p in (batou_project / "stubs").rglob("*")
            if p.is_file()
        )
        assert first_files == second_files


# ---------------------------------------------------------------------------
# 6. Existing Config Protection
# ---------------------------------------------------------------------------


class TestExistingConfigProtection:
    """Setup aborts when unmanaged checker sections already exist."""

    def test_exits_one_on_unmanaged_tool_ty(self, batou_project: Path) -> None:
        """batou-type setup exits 1 if [tool.ty] exists without marker."""
        (batou_project / "pyproject.toml").write_text(
            '[project]\nname = "myproject"\nversion = "0.1.0"\n\n[tool.ty]\nextra-search-paths = ["custom"]\n'
        )
        result = run_cli("setup", str(batou_project))
        assert result.returncode == 1

    def test_error_mentions_conflicting_section(self, batou_project: Path) -> None:
        """Error message mentions the conflicting [tool.ty] section."""
        (batou_project / "pyproject.toml").write_text(
            '[project]\nname = "myproject"\nversion = "0.1.0"\n\n[tool.ty]\nextra-search-paths = ["custom"]\n'
        )
        result = run_cli("setup", str(batou_project))
        output = (result.stdout + result.stderr).lower()
        assert "unmanaged checker sections" in output

    def test_succeeds_on_marked_tool_ty(self, batou_project: Path) -> None:
        """batou-type setup succeeds if [tool.ty] has marker (overwrites)."""
        (batou_project / "pyproject.toml").write_text(
            '[project]\nname = "myproject"\nversion = "0.1.0"\n\n# managed by batou-type setup\n[tool.ty]\nextra-search-paths = ["old"]\n'
        )
        result = run_cli("setup", str(batou_project))
        assert result.returncode == 0

    def test_overwrites_marked_section(self, batou_project: Path) -> None:
        """Marked section is overwritten with fresh config on re-run."""
        (batou_project / "pyproject.toml").write_text(
            '[project]\nname = "myproject"\nversion = "0.1.0"\n\n# managed by batou-type setup\n[tool.ty]\nextra-search-paths = ["old"]\n'
        )
        run_cli("setup", str(batou_project))
        toml = (batou_project / "pyproject.toml").read_text()
        assert 'extra-paths = ["stubs"]' in toml
        assert 'extra-search-paths = ["old"]' not in toml
