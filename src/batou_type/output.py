"""Machine-readable output layer: Pydantic models, converters, and serializers."""

from __future__ import annotations

import json
from collections import defaultdict

from pydantic import BaseModel, ConfigDict, Field

from batou_type.core import TypeCheckResult

_SCHEMA_URL = "https://batou-type.example/schema/v1"


class Diagnostic(BaseModel):
    """A single type-check diagnostic."""

    file: str
    line: int
    column: int | None = None
    end_line: int | None = None
    end_column: int | None = None
    message: str
    hint: str | None = None
    code: str | None = None
    severity: str | None = None
    checker: str


class ComponentResult(BaseModel):
    """Type-check results for a single component file."""

    path: str
    diagnostics: list[Diagnostic]


class ProjectResult(BaseModel):
    """Type-check results for a single project directory."""

    path: str
    components: list[ComponentResult]


class CheckOutput(BaseModel):
    """Top-level machine-readable output envelope."""

    model_config = ConfigDict(populate_by_name=True)

    schema_version: str = "1.0.0"
    projects: list[ProjectResult]
    summary: dict[str, int]
    metadata: dict[str, object] = Field(default_factory=dict)
    schema_url: str = Field(alias="$schema", default=_SCHEMA_URL)


def from_ty_gitlab(raw_json: str) -> list[Diagnostic]:
    """Convert ty GitLab Code Quality JSON to list of Diagnostic.

    Handles both ty's actual format (positions.begin.line) and
    a simplified format (lines.begin) for test compatibility.
    """
    issues = json.loads(raw_json)
    diagnostics: list[Diagnostic] = []
    for issue in issues:
        location = issue["location"]
        # ty uses "positions" key with nested begin/end dicts
        positions = location.get("positions")
        if positions:
            begin = positions["begin"]
            line = begin["line"]
            column = begin.get("column")
            end = positions.get("end", {})
            end_line = end.get("line")
            end_column = end.get("column")
        else:
            line = location["lines"]["begin"]
            column = None
            end_line = None
            end_column = None

        diagnostics.append(
            Diagnostic(
                file=location["path"],
                line=line,
                column=column,
                end_line=end_line,
                end_column=end_column,
                message=issue["description"],
                code=issue.get("check_name"),
                severity=issue.get("severity"),
                checker="ty",
            )
        )
    return diagnostics


def from_mypy_jsonl(raw_output: str) -> list[Diagnostic]:
    """Convert mypy JSON Lines output to list of Diagnostic."""
    diagnostics: list[Diagnostic] = []
    for line in raw_output.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        entry = json.loads(line)
        diagnostics.append(
            Diagnostic(
                file=entry["file"],
                line=entry["line"],
                column=entry.get("column"),
                message=entry["message"],
                hint=entry.get("note"),
                code=entry.get("error_code"),
                severity=entry.get("severity"),
                checker="mypy",
            )
        )
    return diagnostics


def build_output(
    results: list[TypeCheckResult],
    *,
    metadata: dict | None = None,
) -> CheckOutput:
    """Convert TypeCheckResult dataclasses to a CheckOutput Pydantic model."""
    metadata = metadata or {}

    file_diagnostics: dict[str, list[Diagnostic]] = defaultdict(list)
    project_path = "."

    for result in results:
        errors = getattr(result, "errors", None) or []
        file_diagnostics[result.path].extend(errors)

    components = [
        ComponentResult(path=path, diagnostics=diags)
        for path, diags in sorted(file_diagnostics.items())
    ]

    total_errors = sum(len(c.diagnostics) for c in components)

    project = ProjectResult(path=project_path, components=components)

    return CheckOutput(
        projects=[project],
        summary={
            "total_projects": 1,
            "total_components": len(components),
            "total_errors": total_errors,
        },
        metadata=metadata,
    )


def export_schema() -> dict:
    """Return JSON Schema for the CheckOutput model."""
    return CheckOutput.model_json_schema()
