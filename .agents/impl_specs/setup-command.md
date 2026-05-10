---
lifecycle:
  requirements:
    completed_at: "2026-05-10T12:00:00Z"
    git_rev: "4a9b706"
  design:
    completed_at: "2026-05-10T12:30:00Z"
    git_rev: "4a9b706"
  plan:
    completed_at: "2026-05-11T09:00:00Z"
    git_rev: "a15d442"
  workflow:
    completed_at: "2026-05-11T10:00:00Z"
    git_rev: "3cbb921"
  verify:
---

# setup-command

## Context

batou-type wraps type checking for batou deployment projects — it resolves stubs, discovers components, and orchestrates checker invocations. Users currently must run `batou-type check` as the only way to type-check. The `setup` subcommand configures a project so that `ty check`, `mypy`, and `pyright` work natively without the batou-type wrapper, enabling IDE integration via LSP.

## Decisions

### stub-source

#### Context

`batou-stubs` and `batou_ext-stubs` are not published on PyPI. They exist only as vendored stubs inside batou-type's `src/batou_type/vendor/` directory.

#### Decision

Copy vendored stubs from batou-type's `vendor/` into the target project as `stubs/batou/` and `stubs/batou_ext/`. These are PEP 561 stub packages. Checker configs reference `stubs/` via search-path settings.

#### Alternatives

a. Editable pip install of vendor/ — Breaks when batou-type is uninstalled.
b. Publish stubs on PyPI first — Larger scope, separate work item.

#### Consequences

No network access required. Stubs are pinned to the batou-type version that ran setup. Updating requires re-running `batou-type setup` (idempotent).

### module-placement

#### Context

AGENTS.md pre-defines architecture rules for `setup.py`: stdlib + structlog only, no imports from other batou_type modules, cli.py imports from setup.py.

#### Decision

New module `src/batou_type/setup.py`. Enforced by pytest-archon: no typer/rich/pytest/pydantic/libcst imports, no batou_type imports, cross-layer isolation with pytest_plugin.

#### Alternatives

a. Inline in cli.py — cli.py is already 652 lines, violates separation of concerns.

#### Consequences

Architecture rules in test_architecture.py need extending (~5 new rules). AGENTS.md layer diagram needs updating. cli.py gains an import from setup.py.

### pyproject-write

#### Context

Setup reads and writes pyproject.toml. Python 3.13 provides `tomllib` (read-only). Writing requires a separate library.

#### Decision

Add `tomli-w` as a production dependency. Read with `tomllib`, write with `tomli_w`. Correct TOML roundtripping preserves existing content.

#### Alternatives

a. String manipulation — Fragile with TOML's table syntax and edge cases.

#### Consequences

One new production dependency. Setup reads existing pyproject.toml into a dict, adds checker sections, writes back.

### checker-install

#### Context

Setup writes checker configuration. Whether it also installs type checkers (ty, mypy, pyright) is a scope question.

#### Decision

Config only — does NOT install type checkers. Zero package installation logic. No uv/pip subprocess calls.

#### Alternatives

a. Config + install ty — Requires uv integration and venv detection.
b. Config + install all — Too opinionated.

#### Consequences

Setup works without uv in PATH. Cleaner separation: setup = configuration, package management = user responsibility.

### existing-config

#### Context

A project may already have `[tool.ty]`, `[tool.mypy]`, or `[tool.pyright]` sections.

#### Decision

If any target section already exists without the setup marker, abort with error listing conflicting sections. If sections exist with the marker (from a previous setup run), overwrite them (idempotent).

#### Alternatives

a. Merge — Risk of corrupting hand-tuned config.

#### Consequences

Setup is safe — never silently modifies existing checker config. Error message suggests manual integration.

### idempotency

#### Context

Users may run setup multiple times.

#### Decision

Idempotent. Comment marker `# managed by batou-type setup` identifies setup-managed sections. On re-run: overwrite marked sections, abort on unmarked existing sections.

#### Alternatives

a. Guard file — Hidden state, unclear lifecycle.
b. Always overwrite — Loses manual config.

#### Consequences

Safe re-runs. User can distinguish setup-managed from hand-tuned config in pyproject.toml.

### ty-config-content

#### Decision

Write:
- `[tool.ty.src]` with `include = ["components"]`
- `[tool.ty]` with `extra-search-paths = ["stubs"]`

Mirrors what core.py passes via `--extra-search-path` + per-file paths.

### mypy-config-content

#### Decision

Write `[tool.mypy]`:
- `mypy_path = "stubs"`
- `explicit_package_bases = true`
- `check_untyped_defs = true`
- `modules = ["components"]`

Matches core.py mypy flags.

### pyright-config-content

#### Decision

Write `[tool.pyright]`:
- `include = ["components"]`
- `stubPath = "stubs"`

Minimal but sufficient for batou projects.

### cli-interface

#### Decision

`batou-type setup [PATH] [--checkers ty,mypy,pyright] [--dry-run]`. PATH defaults to cwd. `--checkers` selects which checkers to configure (default: all three). `--dry-run` shows what would change without writing.

### error-communication

#### Decision

Simple one-line errors, exit code 1. No structured four-part format. Exit codes: 0 = success, 1 = error.

### missing-pyproject

#### Decision

Create minimal pyproject.toml with `[project]` header (name from directory name, `version = "0.1.0"`) plus checker sections.

### test-strategy

#### Decision

Two test layers: (1) E2E subprocess tests via `run_cli("setup", ...)` with `tmp_path` projects in `test_functional.py`, (2) pytest-archon rules for setup.py in `test_architecture.py`. Spec validation tests in `tests/impl_spec/test_setup_command.py`. 0% mock ratio.

## Requirements

### CLI Usage Examples

```
batou-type setup                          # configure all checkers in cwd
batou-type setup /path/to/deployment      # configure specific project
batou-type setup --checkers ty            # only ty config
batou-type setup --dry-run                # preview changes
```

### Help Text

`batou-type setup --help` shows:
- Description: "Configure project for IDE-native type checking"
- Arguments: PATH (optional, default: current directory)
- Options: --checkers, --dry-run

### Discovery

- `batou-type --help` lists `setup` alongside `version` and `check`
- README.md usage section documents setup
- docs/user/quickstart.md includes "first-time setup" step

### Error Modes

- No `components/` directory → "Not a batou project: {path}"
- Existing checker section without marker → "Existing [tool.ty] section — remove or rename first"
- Permission error on pyproject.toml → OS error propagated

### Documentation

- README.md: usage section updated
- docs/user/quickstart.md: first-time setup step
- docs/user/usage.md: setup subcommand reference

## Appendix

```yaml
# implementation_plan
id: setup-command
description: "Add batou-type setup subcommand — copies vendored stubs, writes ty/mypy/pyright config to pyproject.toml"
created_at: "2026-05-11T09:00:00Z"
git_rev: "a15d442"
specs:
  - .agents/impl_specs/setup-command.md
target_tests:
  - file: tests/impl_spec/test_setup_command.py
    tests:
      - TestSetupModuleArchitecture::test_setup_module_exists
      - TestSetupModuleArchitecture::test_setup_no_typer
      - TestSetupModuleArchitecture::test_setup_no_rich
      - TestSetupModuleArchitecture::test_setup_no_pytest
      - TestSetupModuleArchitecture::test_setup_no_pydantic
      - TestSetupModuleArchitecture::test_setup_no_libcst
      - TestSetupModuleArchitecture::test_setup_no_stogger
      - TestSetupModuleArchitecture::test_setup_no_batou_type_imports
      - TestSetupModuleArchitecture::test_cli_may_import_setup
      - TestSetupCLIRegistration::test_setup_help_exits_zero
      - TestSetupCLIRegistration::test_setup_help_shows_description
      - TestSetupCLIRegistration::test_setup_help_shows_options
      - TestSetupCLIRegistration::test_root_help_lists_setup
      - TestSetupCLIRegistration::test_setup_non_project_path_exits_one
      - TestSetupCLIRegistration::test_setup_dry_run_exits_zero
      - TestSetupCLIRegistration::test_setup_checkers_ty_only
      - TestStubCopying::test_stubs_batou_dir_created
      - TestStubCopying::test_stubs_batou_ext_dir_created
      - TestStubCopying::test_stubs_contain_pyi_files
      - TestStubCopying::test_stubs_have_py_typed_markers
      - TestStubCopying::test_stub_content_matches_vendor
      - TestPyprojectWriting::test_creates_pyproject_if_missing
      - TestPyprojectWriting::test_new_pyproject_has_name_and_version
      - TestPyprojectWriting::test_writes_tool_ty_section
      - TestPyprojectWriting::test_writes_tool_ty_src_section
      - TestPyprojectWriting::test_writes_tool_mypy_section
      - TestPyprojectWriting::test_writes_tool_pyright_section
      - TestPyprojectWriting::test_managed_marker_present
      - TestIdempotency::test_second_run_succeeds
      - TestIdempotency::test_second_run_preserves_config
      - TestIdempotency::test_second_run_preserves_stubs
      - TestExistingConfigProtection::test_exits_one_on_unmanaged_tool_ty
      - TestExistingConfigProtection::test_error_mentions_conflicting_section
      - TestExistingConfigProtection::test_succeeds_on_marked_tool_ty
      - TestExistingConfigProtection::test_overwrites_marked_section
```
