"""Tests for the output layer: Pydantic models, converters, and serializers."""

import json

from pydantic import BaseModel

from batou_type.core import TypeCheckResult
from batou_type.output import (
    CheckOutput,
    Diagnostic,
    build_output,
    export_schema,
    from_mypy_jsonl,
    from_ty_gitlab,
)


class TestDiagnosticModel:
    """Diagnostic Pydantic model structure and defaults."""

    def test_creation_with_required_fields(self):
        diag = Diagnostic(
            file="components/foo.py",
            line=10,
            message="Incompatible return type",
            checker="ty",
        )
        assert diag.file == "components/foo.py"
        assert diag.line == 10
        assert diag.message == "Incompatible return type"
        assert diag.checker == "ty"

    def test_optional_fields_default_none(self):
        diag = Diagnostic(
            file="x.py",
            line=1,
            message="err",
            checker="mypy",
        )
        assert diag.column is None
        assert diag.end_line is None
        assert diag.end_column is None
        assert diag.hint is None
        assert diag.code is None
        assert diag.severity is None

    def test_is_pydantic_base_model(self):
        assert issubclass(Diagnostic, BaseModel)


class TestFromTyGitlab:
    """from_ty_gitlab converter: GitLab Code Quality JSON → Diagnostic."""

    def test_conversion_of_gitlab_json(self):
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

    def test_field_mapping(self):
        gitlab_input = json.dumps(
            [
                {
                    "type": "issue",
                    "check_name": "arg-type",
                    "description": "Bad argument type",
                    "severity": "minor",
                    "fingerprint": "xyz",
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
        assert diag.message == "Bad argument type"
        assert diag.code == "arg-type"
        assert diag.severity == "minor"
        assert diag.checker == "ty"

    def test_empty_array(self):
        diags = from_ty_gitlab("[]")
        assert diags == []

    def test_missing_column(self):
        gitlab_input = json.dumps(
            [
                {
                    "type": "issue",
                    "check_name": "type-error",
                    "description": "Error",
                    "severity": "major",
                    "fingerprint": "f1",
                    "location": {
                        "path": "components/x.py",
                        "lines": {"begin": 1},
                    },
                }
            ]
        )
        diag = from_ty_gitlab(gitlab_input)[0]
        assert diag.column is None


class TestFromMypyJsonl:
    """from_mypy_jsonl converter: mypy JSON Lines → Diagnostic."""

    def test_conversion_of_jsonl(self):
        mypy_input = (
            '{"file": "components/foo.py", "line": 10, "column": 5, '
            '"message": "Incompatible types", "severity": "error"}\n'
        )
        diags = from_mypy_jsonl(mypy_input)
        assert len(diags) == 1
        assert isinstance(diags[0], Diagnostic)

    def test_field_mapping(self):
        mypy_input = (
            '{"file": "components/baz.py", "line": 20, "column": 8, '
            '"message": "Argument 1 has incompatible type", '
            '"severity": "error", "code": "arg-type"}\n'
        )
        diag = from_mypy_jsonl(mypy_input)[0]
        assert diag.file == "components/baz.py"
        assert diag.line == 20
        assert diag.column == 8
        assert diag.message == "Argument 1 has incompatible type"
        assert diag.code == "arg-type"
        assert diag.checker == "mypy"

    def test_multiple_lines(self):
        mypy_input = (
            '{"file": "a.py", "line": 1, "column": 1, '
            '"message": "err1", "severity": "error"}\n'
            '{"file": "b.py", "line": 2, "column": 1, '
            '"message": "err2", "severity": "error"}\n'
        )
        diags = from_mypy_jsonl(mypy_input)
        assert len(diags) == 2
        assert diags[0].file == "a.py"
        assert diags[1].file == "b.py"

    def test_empty_input(self):
        diags = from_mypy_jsonl("")
        assert diags == []


class TestBuildOutput:
    """build_output serializer: TypeCheckResult list → CheckOutput."""

    def test_with_empty_results(self):
        output = build_output([])
        assert isinstance(output, CheckOutput)
        assert output.projects[0].components == []
        assert output.summary["total_projects"] == 1
        assert output.summary["total_components"] == 0
        assert output.summary["total_errors"] == 0

    def test_with_results_no_errors(self):
        results = [
            TypeCheckResult(
                path="components/foo.py",
                has_errors=False,
                output="",
            ),
        ]
        output = build_output(results)
        assert isinstance(output, CheckOutput)
        assert len(output.projects) == 1
        assert output.summary["total_components"] == 1
        assert output.summary["total_errors"] == 0

    def test_summary_computation(self):
        results = [
            TypeCheckResult(
                path="components/a.py",
                has_errors=True,
                output="err",
            ),
            TypeCheckResult(
                path="components/b.py",
                has_errors=False,
                output="",
            ),
        ]
        output = build_output(results)
        assert output.summary["total_projects"] == 1
        assert output.summary["total_components"] == 2
        # No errors attached yet (core.py lacks errors field)
        assert output.summary["total_errors"] == 0


class TestExportSchema:
    """export_schema: CheckOutput JSON Schema export."""

    def test_returns_dict(self):
        schema = export_schema()
        assert isinstance(schema, dict)

    def test_has_type_and_properties(self):
        schema = export_schema()
        assert "properties" in schema
        assert "projects" in schema["properties"]
        assert "summary" in schema["properties"]
