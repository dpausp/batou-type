"""E2E tests for version command and __main__.py trampoline."""


def test_version_shows_batou_type_version(tmp_path, run_cli) -> None:
    """Version command shows batou-type version."""
    result = run_cli("version", cwd=tmp_path)
    assert result.returncode == 0
    assert "batou-type" in (result.stdout + result.stderr).lower()


def test_version_shows_stub_info(tmp_path, run_cli) -> None:
    """Version command shows stub package info."""
    result = run_cli("version", cwd=tmp_path)
    assert "batou-stubs" in (result.stdout + result.stderr).lower()


# --- __main__.py trampoline ---


def test_python_m_version(tmp_path, run_cli) -> None:
    """python -m batou_type version exercises __main__.py trampoline."""
    result = run_cli("version", cwd=tmp_path)
    assert result.returncode == 0
    assert "batou-type" in (result.stdout + result.stderr).lower()


def test_python_m_help(tmp_path, run_cli) -> None:
    """python -m batou_type --help exercises __main__.py trampoline."""
    result = run_cli("--help", cwd=tmp_path)
    assert result.returncode == 0
    assert "check" in result.stdout.lower()
    assert "version" in result.stdout.lower()


def test_python_m_no_args(tmp_path, run_cli) -> None:
    """python -m batou_type with no args shows help/usage."""
    result = run_cli(cwd=tmp_path)
    # Typer exits 2 when no command given, but shows help
    assert result.returncode == 2
    assert "check" in result.stdout.lower()
