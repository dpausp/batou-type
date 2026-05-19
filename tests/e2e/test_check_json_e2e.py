"""E2E tests for --json and --show-schema CLI flags."""


def test_json_clean_component_valid_json(temp_project, run_cli, extract_json) -> None:
    """Clean component produces valid JSON with expected structure."""
    component = temp_project / "components" / "mycomponent.py"
    component.write_text("def configure():\n    pass\n")

    result = run_cli("check", "--json", cwd=temp_project)
    assert result.returncode == 0
    data = extract_json(result.stdout)
    assert "schema_version" in data
    assert "projects" in data
    assert len(data["projects"]) == 1
    assert data["summary"]["total_errors"] == 0
    assert "$schema" not in data


def test_json_component_with_error(temp_project, run_cli, extract_json) -> None:
    """Component with type error produces JSON with diagnostics."""
    component = temp_project / "components" / "badcomponent.py"
    component.write_text("def configure() -> int:\n    return 'not an int'\n")

    result = run_cli("check", "--json", cwd=temp_project)
    assert result.returncode == 1
    data = extract_json(result.stdout)
    assert data["summary"]["total_errors"] == 1
    diags = data["projects"][0]["components"][0]["diagnostics"]
    assert len(diags) > 0
    assert diags[0]["checker"] == "ty"
    assert isinstance(diags[0]["message"], str) and len(diags[0]["message"]) > 0
    assert "badcomponent.py" in diags[0]["file"]


def test_json_no_projects(tmp_path, run_cli, extract_json) -> None:
    """No batou projects produces valid JSON with empty components."""
    result = run_cli("check", "--json", cwd=tmp_path)
    assert result.returncode == 0
    data = extract_json(result.stdout)
    assert data["projects"][0]["components"] == []


def test_show_schema(tmp_path, run_cli, extract_json) -> None:
    """--show-schema outputs valid JSON Schema."""
    result = run_cli("check", "--show-schema", cwd=tmp_path)
    assert result.returncode == 0
    data = extract_json(result.stdout)
    assert "properties" in data
    assert "projects" in data["properties"]


def test_json_stderr_has_logs(temp_project, run_cli) -> None:
    """JSON mode: diagnostics go to stderr, not stdout."""
    component = temp_project / "components" / "mycomponent.py"
    component.write_text("def configure():\n    pass\n")

    result = run_cli("check", "--json", cwd=temp_project)
    assert len(result.stderr) > 0
    assert "Loaded stubs" not in result.stdout
    assert "Found" not in result.stdout
