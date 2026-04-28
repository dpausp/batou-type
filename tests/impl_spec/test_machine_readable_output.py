"""Spec validation tests for machine-readable-output.

These tests validate the output.py module, core.py json_mode changes,
and CLI JSON output functionality.
"""

import inspect
import json
import subprocess
import sys
import pytest


BATOU_TYPE_CLI = [sys.executable, "-m", "batou_type"]


@pytest.fixture
def temp_project(tmp_path):
    """Create a temporary batou project with components directory."""
    components = tmp_path / "components"
    components.mkdir()
    return tmp_path


def run_cli(*args, cwd=None):
    """Run batou-type CLI and return result."""
    result = subprocess.run(
        [*BATOU_TYPE_CLI, *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    return result


# ---------------------------------------------------------------------------
# 1. output.py module exists and exports correctly
# ---------------------------------------------------------------------------


class TestOutputModuleImports:
    """Decision: module-structure — output.py with Pydantic models and converters."""

    def test_import_models(self):
        """CheckOutput, ProjectResult, ComponentResult, Diagnostic importable."""
        from batou_type.output import (
            CheckOutput,
            ComponentResult,
            Diagnostic,
            ProjectResult,
        )

        assert CheckOutput is not None
        assert ProjectResult is not None
        assert ComponentResult is not None
        assert Diagnostic is not None

    def test_import_build_and_schema(self):
        """build_output and export_schema functions importable."""
        from batou_type.output import build_output, export_schema

        assert callable(build_output)
        assert callable(export_schema)

    def test_import_converters(self):
        """from_ty_gitlab and from_mypy_jsonl converters importable."""
        from batou_type.output import from_mypy_jsonl, from_ty_gitlab

        assert callable(from_ty_gitlab)
        assert callable(from_mypy_jsonl)


# ---------------------------------------------------------------------------
# 2. Diagnostic model structure
# ---------------------------------------------------------------------------


class TestDiagnosticModel:
    """Decision: unified-diagnostic-model — single Diagnostic Pydantic model."""

    def test_diagnostic_has_required_fields(self):
        """Diagnostic model has all fields from the unified model spec."""
        from pydantic import BaseModel

        from batou_type.output import Diagnostic

        assert issubclass(Diagnostic, BaseModel)
        field_names = set(Diagnostic.model_fields)
        expected = {
            "file",
            "line",
            "column",
            "end_line",
            "end_column",
            "message",
            "hint",
            "code",
            "severity",
            "checker",
        }
        assert expected == field_names, f"Missing fields: {expected - field_names}"

    def test_diagnostic_optional_fields_default_none(self):
        """Missing fields default to None (ty has no column, etc.)."""
        from batou_type.output import Diagnostic

        diag = Diagnostic(
            file="components/foo.py",
            line=10,
            message="Incompatible return type",
            checker="ty",
        )
        assert diag.column is None
        assert diag.end_line is None
        assert diag.end_column is None
        assert diag.hint is None
        assert diag.code is None
        assert diag.severity is None


# ---------------------------------------------------------------------------
# 3. CheckOutput model structure
# ---------------------------------------------------------------------------


class TestCheckOutputModel:
    """Decision: output-format-json — single comprehensive JSON output."""

    def test_check_output_has_projects_and_summary(self):
        """CheckOutput model has projects list and summary section."""
        from batou_type.output import CheckOutput

        field_names = set(CheckOutput.model_fields)
        assert "projects" in field_names
        assert "summary" in field_names

    def test_check_output_schema_generated(self):
        """CheckOutput can produce a JSON Schema via model_json_schema()."""
        from batou_type.output import CheckOutput

        schema = CheckOutput.model_json_schema()
        assert isinstance(schema, dict)
        assert "properties" in schema
        assert "projects" in schema["properties"]
        assert "summary" in schema["properties"]


# ---------------------------------------------------------------------------
# 4. from_ty_gitlab converter
# ---------------------------------------------------------------------------


class TestFromTyGitlabConverter:
    """Decision: unified-diagnostic-model — ty GitLab Code Quality → Diagnostic."""

    def test_converts_gitlab_json_array(self):
        """A GitLab Code Quality JSON array maps to list of Diagnostic."""
        from batou_type.output import Diagnostic, from_ty_gitlab

        gitlab_input = json.dumps(
            [
                {
                    "type": "issue",
                    "check_name": "type-error",
                    "description": "Incompatible return type",
                    "categories": ["Bug Risk"],
                    "severity": "major",
                    "fingerprint": "abc123",
                    "location": {
                        "path": "components/foo.py",
                        "lines": {"begin": 42},
                    },
                }
            ]
        )

        diags = from_ty_gitlab(gitlab_input)
        assert len(diags) == 1
        assert isinstance(diags[0], Diagnostic)

    def test_ty_fields_mapped_correctly(self):
        """Fields from ty GitLab format are correctly mapped."""
        from batou_type.output import from_ty_gitlab

        gitlab_input = json.dumps(
            [
                {
                    "type": "issue",
                    "check_name": "type-error",
                    "description": "Incompatible types in assignment",
                    "severity": "major",
                    "fingerprint": "def456",
                    "location": {
                        "path": "components/bar.py",
                        "lines": {"begin": 15},
                    },
                }
            ]
        )

        diag = from_ty_gitlab(gitlab_input)[0]
        assert diag.file == "components/bar.py"
        assert diag.line == 15
        assert diag.message == "Incompatible types in assignment"
        assert diag.checker == "ty"

    def test_ty_has_no_column(self):
        """ty GitLab format has no column info — field stays None."""
        from batou_type.output import from_ty_gitlab

        gitlab_input = json.dumps(
            [
                {
                    "type": "issue",
                    "check_name": "type-error",
                    "description": "Error",
                    "severity": "major",
                    "fingerprint": "xyz",
                    "location": {
                        "path": "components/x.py",
                        "lines": {"begin": 1},
                    },
                }
            ]
        )

        diag = from_ty_gitlab(gitlab_input)[0]
        assert diag.column is None


# ---------------------------------------------------------------------------
# 5. from_mypy_jsonl converter
# ---------------------------------------------------------------------------


class TestFromMypyJsonlConverter:
    """Decision: unified-diagnostic-model — mypy JSONL → Diagnostic."""

    def test_converts_mypy_jsonl_lines(self):
        """mypy JSONL lines map to list of Diagnostic."""
        from batou_type.output import Diagnostic, from_mypy_jsonl

        mypy_input = (
            '{"file": "components/foo.py", "line": 10, "column": 5, '
            '"message": "Incompatible types", "severity": "error"}\n'
        )

        diags = from_mypy_jsonl(mypy_input)
        assert len(diags) == 1
        assert isinstance(diags[0], Diagnostic)

    def test_mypy_fields_mapped_correctly(self):
        """Fields from mypy JSON format are correctly mapped."""
        from batou_type.output import from_mypy_jsonl

        mypy_input = (
            '{"file": "components/baz.py", "line": 20, "column": 8, '
            '"message": "Argument 1 has incompatible type", '
            '"severity": "error", "error_code": "arg-type"}\n'
        )

        diag = from_mypy_jsonl(mypy_input)[0]
        assert diag.file == "components/baz.py"
        assert diag.line == 20
        assert diag.column == 8
        assert diag.message == "Argument 1 has incompatible type"
        assert diag.checker == "mypy"

    def test_mypy_multiple_lines(self):
        """Multiple JSONL lines produce multiple diagnostics."""
        from batou_type.output import from_mypy_jsonl

        mypy_input = (
            '{"file": "a.py", "line": 1, "column": 1, '
            '"message": "err1", "severity": "error"}\n'
            '{"file": "b.py", "line": 2, "column": 1, '
            '"message": "err2", "severity": "error"}\n'
        )

        diags = from_mypy_jsonl(mypy_input)
        assert len(diags) == 2


# ---------------------------------------------------------------------------
# 6. build_output function
# ---------------------------------------------------------------------------


class TestBuildOutputFunction:
    """Decision: typecheckresult-coexistence — dataclass → Pydantic converter."""

    def test_build_output_maps_results(self):
        """build_output takes TypeCheckResult list and returns CheckOutput."""
        from batou_type.core import TypeCheckResult
        from batou_type.output import CheckOutput, build_output

        results = [
            TypeCheckResult(
                path="components/foo.py",
                has_errors=False,
                output="",
            ),
        ]

        output = build_output(results, metadata={"checker": ["ty"]})
        assert isinstance(output, CheckOutput)

    def test_build_output_with_errors(self):
        """build_output maps TypeCheckResult with errors to diagnostics."""
        from batou_type.core import TypeCheckResult
        from batou_type.output import Diagnostic, build_output

        results = [
            TypeCheckResult(
                path="components/bad.py",
                has_errors=True,
                output="error output",
                errors=[
                    Diagnostic(
                        file="components/bad.py",
                        line=5,
                        message="Type mismatch",
                        checker="ty",
                    )
                ],
            ),
        ]

        output = build_output(results, metadata={"checker": ["ty"]})
        assert len(output.projects) == 1
        project = output.projects[0]
        assert len(project.components) == 1
        component = project.components[0]
        assert len(component.diagnostics) == 1
        assert component.diagnostics[0].message == "Type mismatch"


# ---------------------------------------------------------------------------
# 7. export_schema function
# ---------------------------------------------------------------------------


class TestExportSchema:
    """Decision: schema-export — programmatic schema access."""

    def test_export_schema_returns_dict(self):
        """export_schema() returns a dict with JSON Schema."""
        from batou_type.output import export_schema

        schema = export_schema()
        assert isinstance(schema, dict)

    def test_export_schema_has_type_definitions(self):
        """Schema dict contains type definitions for models."""
        from batou_type.output import export_schema

        schema = export_schema()
        assert "$defs" in schema or "definitions" in schema or "properties" in schema


# ---------------------------------------------------------------------------
# 8. check_file json_mode parameter
# ---------------------------------------------------------------------------


class TestCheckFileJsonMode:
    """Decision: check-file-json-mode — json_mode param on check_file."""

    def test_check_file_accepts_json_mode(self):
        """check_file() accepts json_mode: bool parameter."""
        from batou_type.core import check_file

        sig = inspect.signature(check_file)
        assert "json_mode" in sig.parameters
        param = sig.parameters["json_mode"]
        assert param.default is False

    def test_typecheckresult_has_errors_field(self):
        """TypeCheckResult dataclass has errors: list[Diagnostic] | None."""
        from batou_type.core import TypeCheckResult

        assert "errors" in TypeCheckResult.__dataclass_fields__
        result = TypeCheckResult(path="test.py", has_errors=False, output="")
        assert result.errors is None


# ---------------------------------------------------------------------------
# 9. check_all json_mode parameter
# ---------------------------------------------------------------------------


class TestCheckAllJsonMode:
    """Decision: check-file-json-mode — json_mode param on check_all."""

    def test_check_all_accepts_json_mode(self):
        """check_all() accepts json_mode: bool parameter."""
        from batou_type.core import check_all

        sig = inspect.signature(check_all)
        assert "json_mode" in sig.parameters
        param = sig.parameters["json_mode"]
        assert param.default is False


# ---------------------------------------------------------------------------
# 10. CLI --json flag
# ---------------------------------------------------------------------------


class TestCliJsonFlag:
    """Decision: cli-flag-design — --json / --output-format json on check."""

    def test_json_flag_produces_json_on_stdout(self, temp_project):
        """batou-type check --json outputs valid JSON on stdout."""
        component = temp_project / "components" / "mycomponent.py"
        component.write_text("def configure():\n    pass\n")

        result = run_cli("check", "--json", cwd=temp_project)
        assert result.returncode in (0, 1, 2)
        data = json.loads(result.stdout)
        assert isinstance(data, dict)

    def test_json_mode_diagnostics_on_stderr(self, temp_project):
        """In JSON mode, diagnostic/progress output goes to stderr."""
        component = temp_project / "components" / "mycomponent.py"
        component.write_text("def configure():\n    pass\n")

        result = run_cli("check", "--json", cwd=temp_project)
        # stdout should be pure JSON, diagnostic logging on stderr
        if result.stderr:
            # stderr has diagnostic output, stdout has JSON
            data = json.loads(result.stdout)
            assert isinstance(data, dict)


# ---------------------------------------------------------------------------
# 11. CLI --show-schema flag
# ---------------------------------------------------------------------------


class TestCliShowSchemaFlag:
    """Decision: schema-export — --show-schema prints JSON Schema."""

    def test_show_schema_outputs_json_schema(self):
        """batou-type check --show-schema outputs valid JSON Schema."""
        result = run_cli("check", "--show-schema")
        assert result.returncode == 0
        schema = json.loads(result.stdout)
        assert isinstance(schema, dict)
        # JSON Schema should have type definitions
        assert "$defs" in schema or "properties" in schema or "type" in schema


# ---------------------------------------------------------------------------
# 12. JSON output roundtrip
# ---------------------------------------------------------------------------


class TestJsonOutputRoundtrip:
    """Decision: output-format-json — full JSON roundtrip with error details."""

    def test_roundtrip_with_type_error(self, temp_project):
        """Run --json on a project with a type error: parse and verify structure."""
        component = temp_project / "components" / "badcomponent.py"
        component.write_text("def configure() -> int:\n    return 'not an int'\n")

        result = run_cli("check", "--json", cwd=temp_project)
        assert result.returncode == 1

        data = json.loads(result.stdout)
        assert isinstance(data, dict)

        # Top-level structure
        assert "projects" in data
        assert "summary" in data

        # Projects contain diagnostics
        projects = data["projects"]
        assert len(projects) >= 1
        project = projects[0]
        assert "components" in project

        # At least one component has diagnostics with error details
        components_with_errors = [
            c for c in project["components"] if c.get("diagnostics")
        ]
        assert len(components_with_errors) >= 1

        diag = components_with_errors[0]["diagnostics"][0]
        assert "file" in diag
        assert "line" in diag
        assert "message" in diag
        assert "checker" in diag
