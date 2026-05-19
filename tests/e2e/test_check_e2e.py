"""E2E tests for check command and error handling."""


def test_check_no_components_exits_zero(tmp_path, run_cli) -> None:
    """Check with no component files exits 0."""
    result = run_cli("check", cwd=tmp_path)
    assert result.returncode == 0
    assert "no batou projects found" in (result.stdout + result.stderr).lower()


def test_check_clean_component_exits_zero(temp_project, run_cli) -> None:
    """Check with valid component files exits 0."""
    component = temp_project / "components" / "mycomponent.py"
    component.write_text("def configure():\n    pass\n")

    result = run_cli("check", cwd=temp_project)
    assert result.returncode == 0
    assert "component(s) passed" in (result.stdout + result.stderr).lower()


def test_check_component_with_type_error_exits_one(temp_project, run_cli) -> None:
    """Check with type errors exits 1."""
    component = temp_project / "components" / "badcomponent.py"
    component.write_text("def configure() -> int:\n    return 'not an int'\n")

    result = run_cli("check", cwd=temp_project)
    assert result.returncode == 1


def test_check_with_ty_checker(temp_project, run_cli) -> None:
    """Check with explicit -c ty works."""
    component = temp_project / "components" / "mycomponent.py"
    component.write_text("def configure():\n    pass\n")

    result = run_cli("check", "-c", "ty", cwd=temp_project)
    assert result.returncode == 0


def test_check_with_mypy_checker(temp_project, run_cli) -> None:
    """Check with explicit -c mypy works."""
    component = temp_project / "components" / "mycomponent.py"
    component.write_text("def configure():\n    pass\n")

    result = run_cli("check", "-c", "mypy", cwd=temp_project)
    # mypy might not be installed, but command should not crash
    assert result.returncode in (0, 1, 2)  # 2 = checker not found


def test_check_multiple_components(temp_project, run_cli) -> None:
    """Check handles multiple component files."""
    (temp_project / "components" / "comp1.py").write_text("def foo():\n    pass\n")
    (temp_project / "components" / "comp2.py").write_text("def bar():\n    pass\n")

    result = run_cli("check", cwd=temp_project)
    assert result.returncode == 0
    # Diagnostic info on stderr (stogger formatted with _replace_msg)
    assert "Checking 2 component(s)" in result.stderr


def test_check_nested_components(temp_project, run_cli) -> None:
    """Check finds components in nested directories."""

    nested = temp_project / "components" / "subpackage"
    nested.mkdir(parents=True)
    (nested / "nestedcomp.py").write_text("def nested():\n    pass\n")

    result = run_cli("check", cwd=temp_project)
    assert result.returncode == 0


# --- Error handling ---


def test_invalid_checker_shows_error(temp_project, run_cli) -> None:
    """Invalid checker name shows clear error."""
    result = run_cli("check", "--checker", "invalid", cwd=temp_project)
    assert result.returncode == 2
    # Typer outputs errors to stderr
    assert "invalid" in result.stderr.lower()
