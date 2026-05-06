# Test Architecture

## Context

The fixer feature introduced new modules and CLI functionality that needed testing at multiple levels of isolation without compromising the project's 0% mock ratio policy.

## Decisions

### test-strategy

#### Context

Fixer transformations are pure functions (source string in, source string out), but the CLI pipeline involves real subprocess invocation of type checkers and real file I/O. A single test tier cannot cover both effectively.

#### Decision

Two-tier testing: (1) Unit tests pass source string + `Diagnostic` objects to `fixer.apply()`, assert on output string comparison. No subprocess, no ty invocation. (2) Integration tests call `run_fix()` on `tmp_path` projects with real component files, real ty invocations, real file operations.

#### Alternatives

a. Mock `check_all()` to return fixed diagnostics — rejected because it would not test the real diagnostic grouping, file I/O, or type checker interaction; violates the 0% mock ratio policy.
b. Only E2E subprocess tests — rejected because subprocess tests are slow and provide poor error localization; a failing assertion in a subprocess test requires debugging the entire pipeline rather than the specific transformation.

#### Consequences

Unit tests are fast and provide precise failure localization. They cover edge cases (empty source, invalid Python, no-op paths) without needing a type checker installed. Integration tests verify the full pipeline end-to-end with real type checker output, real file writes, and real exit codes.

### architecture-test-impact

#### Context

Adding `fixer.py` to the codebase introduced a new module in the layer graph. The existing architecture enforcement in `test_architecture.py` needed extension to prevent the fixer from importing frameworks or upper-layer modules.

#### Decision

Architecture constraints are enforced at test time by pytest-archon rules in `tests/test_architecture.py`. `fixer.py` layer rules: no typer, no rich, no pytest, no structlog, no stogger, no cli import, no pytest_plugin import, only `output.py` from `batou_type`.

#### Alternatives

a. Runtime import guards using `sys.modules` hooks — rejected because they only catch violations at execution time, not at import analysis time; also add complexity to production code for testing purposes.
b. Linting rules (ruff import constraints) — rejected because ruff's import restriction is file-level, not module-level; pytest-archon checks the actual resolved import graph against the package structure.

#### Consequences

Any PR that accidentally adds a framework import to `fixer.py` (e.g., importing typer for error reporting) will fail CI immediately. The architecture rules are declarative and live alongside the code they constrain, making them discoverable and maintainable. The same rules are duplicated in `tests/impl_spec/test_autofix_missing_imports.py::TestFixerArchitecture` for spec validation.

## Verified By

- `tests/test_architecture.py::TestFixerLayer` — enforces all fixer.py layer constraints (7 rules)
- `tests/test_architecture.py::TestCrossLayerIsolation::test_cli_may_import_fixer` — enforces cli → fixer dependency direction
- `tests/impl_spec/test_autofix_missing_imports.py::TestFixerArchitecture` — duplicate architecture rules for spec validation
- `tests/test_fixer.py` — unit tests for both fixers with 0% mock ratio
- `tests/test_fixer_integration.py` — integration tests for `run_fix()` pipeline with real ty invocations
- `tests/test_functional.py` — E2E subprocess tests exercising the CLI fix flags
