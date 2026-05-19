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
