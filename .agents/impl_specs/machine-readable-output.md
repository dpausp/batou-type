---
lifecycle:
  requirements:
    completed_at: "2026-04-28T12:00:00Z"
    git_rev: "9d6d81d"
  design:
    completed_at: "2026-04-28T14:00:00Z"
    git_rev: "9d6d81d"
  implement:
    completed_at: "2026-04-28T16:00:00Z"
    git_rev: "cf84d79"
---

# machine-readable-output

## Context

batou-type produces only human-readable terminal output (Rich). There is no machine-readable format, no schema, and no way to pipe results into LLM tools, CI pipelines, or statistical analysis tools. This spec adds structured JSON output with a complete schema, clean stdout/stderr separation, and stogger-based logging.

## Decisions

### output-transport

#### Context

Output must be consumable by both humans and machines. LLM tools need pipable JSON on stdout. Diagnostic information must not mix with data output.

#### Decision

stdout/stderr split: JSON payload on stdout (pipable), diagnostic logging on stderr via stogger. Default mode remains human-readable on stdout. JSON mode activated via `--json` or `--output-format json` flag.

#### Alternatives

a. Always JSON on stdout + human-readable on stderr — breaks current UX
b. Separate `export` subcommand — extra CLI surface
c. File-based output — not pipeable

#### Consequences

Clean piping: `batou-type check --json . | llm-tool`. Backward-compatible default. Stogger dependency required.

### logging-always-stogger

#### Context

All diagnostic output ("Loaded stubs:", "Found N project(s):", venv info, progress) currently goes to Rich console on stdout, mixed with results. Must move to stderr in both modes.

#### Decision

Stogger always active (both human and JSON mode). All diagnostic `console.print()` calls become `log.info()` → stderr. `console` object kept only for primary human-readable output (error display, check results). `stogger.init_logging()` called at CLI entry point.

#### Alternatives

a. Stogger only in JSON mode — inconsistent between modes
b. Keep console.print alongside stogger — stdout/stderr split not achieved

#### Consequences

Breaking behavioral change: diagnostic info moves from stdout to stderr. Users who parsed stdout for stub info will break — but that was never a supported interface. stogger becomes a dependency.

### output-format-json

#### Context

Need a universal machine-readable format for LLMs, CI/CD, statistics, and debugging.

#### Decision

JSON with snake_case field names. Single comprehensive output: project metadata, stub info, per-project results with per-component diagnostics, and a summary section. Pydantic models define the structure; JSON Schema auto-generated from them.

#### Alternatives

a. JSON Lines — no root object for metadata
b. YAML — harder to parse, less standard
c. Two-tier output (compact + verbose) — adds complexity

#### Consequences

One format, one schema. Pydantic ensures type safety. snake_case consistent with Python codebase.

### module-structure

#### Context

New Pydantic models and serialization need a home. core.py has zero external dependencies and handles check logic. Output layer must not pollute core.

#### Decision

New module `src/batou_type/output.py` containing all Pydantic models (`CheckOutput`, `ProjectResult`, `ComponentResult`, `Diagnostic`), converter functions (`from_ty_gitlab`, `from_mypy_jsonl`), serializer (`build_output`), and schema export (`export_schema`). core.py stays unchanged. cli.py imports from output.py only when JSON mode is active.

#### Alternatives

a. Models in core.py — adds Pydantic dep to core, breaks clean layering
b. Two modules (models.py + output.py) — over-engineering
c. Everything in cli.py — not testable without CLI

#### Consequences

New file. Pydantic dependency. Clean layer separation: core (data) → output (modeling) → cli (presentation).

### check-file-json-mode

#### Context

`check_file()` runs checkers with human-readable flags. Need structured output without breaking existing callers (pytest_plugin uses `check_all()` → `check_file()`).

#### Decision

New parameter `json_mode: bool = False` on `check_file()` and `check_all()`. When True: ty gets `--output-format gitlab` instead of `--color always`, mypy gets `--output json` added. Parsed errors stored as `errors: list[Diagnostic] | None = None` on `TypeCheckResult`. Default False, existing callers unaffected.

#### Alternatives

a. New parallel function — code duplication
b. Post-processing (run twice) — double work
c. Parse raw text — fragile, ignores native JSON

#### Consequences

`TypeCheckResult` gains optional `errors` field. Minimal API change. pytest_plugin unaffected.

### unified-diagnostic-model

#### Context

ty outputs GitLab Code Quality JSON (array), mypy outputs JSONL (one object per line). Fields differ. Consumers need a single model.

#### Decision

Unified `Diagnostic` Pydantic model: `file`, `line`, `column`, `end_line`, `end_column`, `message`, `hint`, `code`, `severity`, `checker`. Converter functions `from_ty_gitlab()` and `from_mypy_jsonl()` map to this model. Missing fields default to None (ty has no column). Consumers see no checker-specific differences.

#### Alternatives

a. Separate models per checker — consumer handles two formats
b. Raw JSON passthrough — consumer must parse both formats
c. Common fields only — loses code, hint, end positions

#### Consequences

One model for all checkers. Slight info loss on ty side (no column in GitLab format).

### typecheckresult-coexistence

#### Context

`TypeCheckResult` is a dataclass used by core.py and pytest_plugin.py. New Pydantic models define the external output contract. Two type systems must coexist.

#### Decision

`TypeCheckResult` stays dataclass, gains `errors: list[Diagnostic] | None = None` field. Pydantic models in output.py are separate, built via converter function `build_output()` that maps dataclass → Pydantic. Two distinct types: dataclass for internal processing, Pydantic for serialization.

#### Alternatives

a. Replace TypeCheckResult with Pydantic — breaks plugin, large refactor
b. Completely independent models — slight duplication but full decoupling

#### Consequences

No migration. Plugin untouched. Converter function bridges the gap.

### schema-export

#### Context

Consumers need access to the JSON Schema for validation and documentation.

#### Decision

Three export paths: (1) `--show-schema` CLI flag outputs schema to stdout, (2) `$schema` property in JSON output points to a stable URL, (3) Python API `batou_type.output.export_schema()` returns dict for programmatic access. Schema generated via Pydantic's `model_json_schema()`.

#### Alternatives

a. CLI flag only — no programmatic access
b. $schema URL only — requires network
c. Python API only — no CLI discovery

#### Consequences

Maximum discoverability. Schema always available offline and online.

### cli-flag-design

#### Context

Must not break existing CLI. JSON mode must be discoverable.

#### Decision

`--output-format json` flag on existing `check` command, with `--json` as shorthand alias. Default remains human-readable (Rich). Single flag, no new subcommands.

#### Alternatives

a. Separate subcommand — more surface, harder to remember
b. Config file based — not pipeable
c. Always JSON on stdout — breaks existing users

#### Consequences

Backward-compatible. `--help` shows the flag. `--json` for quick piping.

### plugin-scope

#### Context

pytest plugin uses `check_all()` and surfaces results via `pytest.fail()`. Question: should plugin gain JSON capability?

#### Decision

Plugin stays as-is. JSON output is a CLI-only feature. Plugin calls `check_all(json_mode=False)` (default). No plugin changes.

#### Alternatives

a. Plugin gets `--batou-ty-json` option — scope creep
b. Plugin uses json_mode internally for better error reports — marginal benefit, extra work

#### Consequences

Zero plugin changes. Clear scope boundary.

### test-strategy

#### Context

New output layer needs coverage. Existing tests cover check logic, CLI, plugin, architecture.

#### Decision

Tests-first. New `tests/test_output.py` for Pydantic models, converters, serializers. Extended `tests/test_functional.py` for `--json` E2E. Coverage: ty→Diagnostic mapping, mypy→Diagnostic mapping, full JSON roundtrip, schema validation, stdout/stderr split. Existing tests untouched.

#### Alternatives

a. E2E only — normalizer logic not isolated
b. No new tests — no schema validation

#### Consequences

New test file. Full output layer coverage before implementation.

## Requirements

### Interface Contracts

**CLI usage:**

```bash
# Human-readable (default, unchanged)
batou-type check [PATHS]

# Machine-readable JSON on stdout
batou-type check --json [PATHS]
batou-type check --output-format json [PATHS]

# Schema export
batou-type check --show-schema

# Piping to LLM tools
batou-type check --json . | llm-tool

# Diagnostic output always on stderr (stogger)
# Both modes: progress, stub info, venv detection → stderr
```

**Help text (`--json`):**

```
  --json, --output-format json
                      Output results as JSON to stdout
```

**Help text (`--show-schema`):**

```
  --show-schema       Print the JSON Schema for the output format and exit
```

**Discovery:** Users find `--json` via `batou-type check --help`. Schema available via `--show-schema` or `$schema` property in output.

**Error communication:** Checker failures appear as structured `Diagnostic` objects in JSON. Infrastructure errors (no checker found, invalid project) logged to stderr via stogger. Exit codes: 0=all pass, 1=failures found, 2=infrastructure error (unchanged).

**Documentation:** JSON output format documented in user docs. Schema file bundled in package. Changelog entry for new feature.

## References

- ty `--output-format gitlab`: https://docs.astral.sh/ty/reference/cli/
- mypy `--output json`: https://mypy.readthedocs.io/en/stable/command_line.html
- GitLab Code Quality spec: https://docs.gitlab.com/ci/testing/code_quality/#code-quality-report-format
- Stogger: ../stogger/packages/stogger

## Appendix

### Implementation Plan

```yaml
id: machine-readable-output
description: "Add structured JSON output mode to batou-type: Pydantic models in output.py, unified Diagnostic model, checker-specific converters (ty GitLab, mypy JSONL), build_output serializer, export_schema, json_mode parameter on check_file/check_all, --json/--output-format json and --show-schema CLI flags, stogger-based logging to stderr."
git_rev: "cf84d79"
created_at: "2026-04-28T16:00:00Z"
target_tests:
  - file: tests/impl_spec/test_machine_readable_output.py
    tests:
      - TestOutputModuleImports::test_import_models
      - TestOutputModuleImports::test_import_build_and_schema
      - TestOutputModuleImports::test_import_converters
      - TestDiagnosticModel::test_diagnostic_has_required_fields
      - TestDiagnosticModel::test_diagnostic_optional_fields_default_none
      - TestCheckOutputModel::test_check_output_has_projects_and_summary
      - TestCheckOutputModel::test_check_output_schema_generated
      - TestFromTyGitlabConverter::test_converts_gitlab_json_array
      - TestFromTyGitlabConverter::test_ty_fields_mapped_correctly
      - TestFromTyGitlabConverter::test_ty_has_no_column
      - TestFromMypyJsonlConverter::test_converts_mypy_jsonl_lines
      - TestFromMypyJsonlConverter::test_mypy_fields_mapped_correctly
      - TestFromMypyJsonlConverter::test_mypy_multiple_lines
      - TestBuildOutputFunction::test_build_output_maps_results
      - TestBuildOutputFunction::test_build_output_with_errors
      - TestExportSchema::test_export_schema_returns_dict
      - TestExportSchema::test_export_schema_has_type_definitions
      - TestCheckFileJsonMode::test_check_file_accepts_json_mode
      - TestCheckFileJsonMode::test_typecheckresult_has_errors_field
      - TestCheckAllJsonMode::test_check_all_accepts_json_mode
      - TestCliJsonFlag::test_json_flag_produces_json_on_stdout
      - TestCliJsonFlag::test_json_mode_diagnostics_on_stderr
      - TestCliShowSchemaFlag::test_show_schema_outputs_json_schema
      - TestJsonOutputRoundtrip::test_roundtrip_with_type_error
```
