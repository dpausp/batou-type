"""E2E tests for help output."""


def test_help_shows_commands(run_cli, strip_ansi) -> None:
    """--help shows available commands."""
    result = run_cli("--help")
    assert result.returncode == 0
    output = strip_ansi(result.stdout.lower())
    assert "check" in output
    assert "version" in output


def test_check_help_shows_options(run_cli, strip_ansi) -> None:
    """check --help shows options."""
    result = run_cli("check", "--help")
    assert result.returncode == 0
    output = strip_ansi(result.stdout.lower())
    assert "--checker" in output


def test_bad_command_shows_error(run_cli) -> None:
    """Invalid command shows error message."""
    result = run_cli("nonexistent")
    assert result.returncode == 2
    # Typer outputs errors to stderr
    assert "no such command" in result.stderr.lower()


# --- Flag presence in help output ---


def test_check_help_shows_fix_flag() -> None:
    """--fix flag present in check --help."""
    import re
    from typer.testing import CliRunner
    from batou_type.cli import app

    runner = CliRunner()
    result = runner.invoke(app, ["check", "--help"])
    assert "--fix" in re.sub(r"\x1b\[[0-9;]*m", "", result.output)


def test_check_help_shows_diff_flag() -> None:
    """--diff flag present in check --help."""
    import re
    from typer.testing import CliRunner
    from batou_type.cli import app

    runner = CliRunner()
    result = runner.invoke(app, ["check", "--help"])
    assert "--diff" in re.sub(r"\x1b\[[0-9;]*m", "", result.output)


def test_check_help_shows_fix_only_flag() -> None:
    """--fix-only flag present in check --help."""
    import re
    from typer.testing import CliRunner
    from batou_type.cli import app

    runner = CliRunner()
    result = runner.invoke(app, ["check", "--help"])
    assert "--fix-only" in re.sub(r"\x1b\[[0-9;]*m", "", result.output)


def test_check_help_shows_virtual_flag() -> None:
    """--virtual flag present in check --help."""
    import re
    from typer.testing import CliRunner
    from batou_type.cli import app

    runner = CliRunner()
    result = runner.invoke(app, ["check", "--help"])
    assert "--virtual" in re.sub(r"\x1b\[[0-9;]*m", "", result.output)


# --- Setup help output ---


def test_setup_help_exits_zero(run_cli) -> None:
    """batou-type setup --help exits 0."""
    result = run_cli("setup", "--help")
    assert result.returncode == 0


def test_setup_help_shows_description(run_cli, strip_ansi) -> None:
    """batou-type setup --help shows 'IDE-native type checking' in description."""
    result = run_cli("setup", "--help")
    output = strip_ansi(result.stdout.lower())
    assert "ide-native type checking" in output


def test_setup_help_shows_checkers_and_dry_run_options(run_cli, strip_ansi) -> None:
    """batou-type setup --help shows --checkers and --dry-run options."""
    result = run_cli("setup", "--help")
    output = strip_ansi(result.stdout.lower())
    assert "--checkers" in output
    assert "--dry-run" in output
