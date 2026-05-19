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


# --- Diagnostic model ---


def test_diagnostic_creation_with_required_fields() -> None:
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


def test_diagnostic_optional_fields_default_none() -> None:
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


def test_diagnostic_is_pydantic_base_model() -> None:
    assert issubclass(Diagnostic, BaseModel)


# --- from_ty_gitlab ---


def test_from_ty_gitlab_conversion() -> None:
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


def test_from_ty_gitlab_field_mapping() -> None:
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


def test_from_ty_gitlab_empty_array() -> None:
    diags = from_ty_gitlab("[]")
    assert diags == []


def test_from_ty_gitlab_missing_column() -> None:
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


# --- from_mypy_jsonl ---


def test_from_mypy_jsonl_conversion() -> None:
    mypy_input = (
        '{"file": "components/foo.py", "line": 10, "column": 5, '
        '"message": "Incompatible types", "severity": "error"}\n'
    )
    diags = from_mypy_jsonl(mypy_input)
    assert len(diags) == 1
    assert isinstance(diags[0], Diagnostic)


def test_from_mypy_jsonl_field_mapping() -> None:
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


def test_from_mypy_jsonl_multiple_lines() -> None:
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


def test_from_mypy_jsonl_empty_input() -> None:
    diags = from_mypy_jsonl("")
    assert diags == []


# --- build_output ---


def test_build_output_with_empty_results() -> None:
    output = build_output([])
    assert isinstance(output, CheckOutput)
    assert output.projects[0].components == []
    assert output.summary["total_projects"] == 1
    assert output.summary["total_components"] == 0
    assert output.summary["total_errors"] == 0


def test_build_output_with_results_no_errors() -> None:
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


def test_build_output_summary_computation() -> None:
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


# --- export_schema ---


def test_export_schema_returns_dict() -> None:
    schema = export_schema()
    assert isinstance(schema, dict)


def test_export_schema_has_type_and_properties() -> None:
    schema = export_schema()
    assert "properties" in schema
    assert "projects" in schema["properties"]
    assert "summary" in schema["properties"]
