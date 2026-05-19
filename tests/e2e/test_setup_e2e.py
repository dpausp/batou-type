"""E2E tests for `batou-type setup` — stub copying, config protection, idempotency."""

from pathlib import Path

VENDOR = Path(__file__).resolve().parent.parent.parent / "src" / "batou_type" / "vendor"


# --- Stub copying ---


def test_setup_stubs_batou_dir_created(run_cli, batou_project: Path) -> None:
    """After setup, stubs/batou/ directory exists."""
    run_cli("setup", str(batou_project))
    assert (batou_project / "stubs" / "batou").is_dir()


def test_setup_stubs_batou_ext_dir_created(run_cli, batou_project: Path) -> None:
    """After setup, stubs/batou_ext/ directory exists."""
    run_cli("setup", str(batou_project))
    assert (batou_project / "stubs" / "batou_ext").is_dir()


def test_setup_stubs_contain_pyi_files(run_cli, batou_project: Path) -> None:
    """Copied stubs contain .pyi files (PEP 561 structure)."""
    run_cli("setup", str(batou_project))
    batou_pyi = list((batou_project / "stubs" / "batou").rglob("*.pyi"))
    batou_ext_pyi = list((batou_project / "stubs" / "batou_ext").rglob("*.pyi"))
    assert len(batou_pyi) > 0, "stubs/batou/ must contain .pyi files"
    assert len(batou_ext_pyi) > 0, "stubs/batou_ext/ must contain .pyi files"


def test_setup_stubs_have_py_typed_markers(run_cli, batou_project: Path) -> None:
    """Copied stub packages include py.typed markers."""
    run_cli("setup", str(batou_project))
    assert (batou_project / "stubs" / "batou" / "py.typed").exists()
    assert (batou_project / "stubs" / "batou_ext" / "py.typed").exists()


def test_setup_stub_content_matches_vendor(run_cli, batou_project: Path) -> None:
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


# --- Idempotency ---


def test_setup_second_run_preserves_stubs(run_cli, batou_project: Path) -> None:
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


# --- Existing config protection ---


def test_setup_exits_one_on_unmanaged_tool_ty(run_cli, batou_project: Path) -> None:
    """batou-type setup exits 1 if [tool.ty] exists without marker."""
    (batou_project / "pyproject.toml").write_text(
        '[project]\nname = "myproject"\nversion = "0.1.0"\n\n[tool.ty]\nextra-search-paths = ["custom"]\n'
    )
    result = run_cli("setup", str(batou_project))
    assert result.returncode == 1


def test_setup_error_mentions_conflicting_section(run_cli, batou_project: Path) -> None:
    """Error message mentions the conflicting checker sections."""
    (batou_project / "pyproject.toml").write_text(
        '[project]\nname = "myproject"\nversion = "0.1.0"\n\n[tool.ty]\nextra-search-paths = ["custom"]\n'
    )
    result = run_cli("setup", str(batou_project))
    output = (result.stdout + result.stderr).lower()
    assert "unmanaged checker sections" in output


def test_setup_succeeds_on_marked_tool_ty(run_cli, batou_project: Path) -> None:
    """batou-type setup succeeds if [tool.ty] has marker (overwrites)."""
    (batou_project / "pyproject.toml").write_text(
        '[project]\nname = "myproject"\nversion = "0.1.0"\n\n# managed by batou-type setup\n[tool.ty]\nextra-search-paths = ["old"]\n'
    )
    result = run_cli("setup", str(batou_project))
    assert result.returncode == 0


def test_setup_overwrites_marked_section(run_cli, batou_project: Path) -> None:
    """Marked section is overwritten with fresh config on re-run."""
    (batou_project / "pyproject.toml").write_text(
        '[project]\nname = "myproject"\nversion = "0.1.0"\n\n# managed by batou-type setup\n[tool.ty]\nextra-search-paths = ["old"]\n'
    )
    run_cli("setup", str(batou_project))
    toml = (batou_project / "pyproject.toml").read_text()
    assert 'extra-paths = ["stubs"]' in toml
    assert 'extra-search-paths = ["old"]' not in toml


# --- Dry run ---


def test_setup_dry_run_no_files_written(run_cli, batou_project: Path) -> None:
    """--dry-run exits 0 and creates no stubs/ or pyproject.toml."""
    result = run_cli("setup", "--dry-run", str(batou_project))
    assert result.returncode == 0
    assert not (batou_project / "stubs").exists()
    assert not (batou_project / "pyproject.toml").exists()
