# Testing

The test suite validates correctness, architecture, and the public API contract with minimal mocking.

Unit and integration tests exercise real code paths with real dependencies: `tmp_path` for filesystem, `pytester` for the plugin, real subprocesses for E2E. The only exception is `test_fixer_integration.py`, which uses `unittest.mock.patch` to isolate CLI flag dispatch logic (checking that `--diff` implies `--fix-only` implies `--fix`). These are the only mocks in the suite.

## Test Files and Their Role

| File | Role |
|------|------|
| `test_core.py` | Unit tests for path detection and component discovery with `tmp_path` |
| `test_output.py` | Unit tests for Pydantic output models, JSON serialization, and schema export |
| `test_fixer.py` | Unit tests for fixer AST transformations — source string in, source string out |
| `test_fixer_integration.py` | Integration tests for `run_fix()` on `tmp_path` projects with real component files |
| `test_pytest_plugin.py` | Integration tests via `pytester` — creates real component files, runs `--batou-ty` |
| `test_functional.py` | E2E tests — spawns `python -m batou_type` as subprocess, asserts on exit codes and output (includes autofix E2E) |
| `test_architecture.py` | Architecture enforcement via `pytest-archon` import rules |
| `test_refactor_contract.py` | AST-based structural contracts (module existence, import boundaries, public API) |
| `test_attribute_types.py` | Attribute type correctness in vendor stubs |
| `test_autofix_missing_imports.py` | Spec validation tests for autofix missing-import fixer |
| `test_setup_command.py` | Spec validation tests for setup command |

| `test_init.py` | Public API importability tests — verifies `__all__` exports are importable |
## Architecture Enforcement

`test_architecture.py` uses `pytest-archon` to enforce the layered structure at import level:

- **Core purity** — `core.py` must not import typer, rich, pytest, or any other `batou_type` module.
- **Framework isolation** — typer and rich are banned outside `cli.py`; pytest is banned outside `pytest_plugin.py`; `__init__.py` must not import either framework directly.
- **Cross-layer isolation** — CLI and plugin must not import each other; `__main__.py` may only import from `cli.py`.
- **Init purity** — `__init__.py` must only import from `core.py`, never from `cli.py` or `pytest_plugin.py`.

These rules specify negative constraints ("must not import X") and check them against the actual import graph, not convention. Accidental layer violations fail at CI time.

## Coverage Characteristics

Coverage reports don't tell the full story. E2E tests invoke the CLI as a subprocess, so coverage tooling never sees the child process.

### Coverage Tiers

| Tier | Modules | What this means |
|------|---------|-----------------|
| **Well-tested** | `core.py`, `output.py`, `fixer.py`, `pytest_plugin.py` | Directly imported by unit and integration tests. Measured coverage reflects real usage. |
| **Functionally tested, measured coverage incomplete** | `cli.py` | E2E subprocess tests in `test_functional.py` exercise every subcommand and flag. Coverage tooling does not see subprocess execution, so measured numbers understate actual coverage. |
| **Trivial** | `__init__.py`, `__main__.py` | Re-exports and a two-line trampoline. No meaningful logic to test beyond what the contract tests verify. |

When reading coverage reports, treat `cli.py` as tested-by-E2E rather than undertested. The subprocess tests assert on exit codes, stdout, and stderr — they verify behavior end-to-end.

## Running Tests

```bash
pytest                              # full suite
pytest tests/test_core.py           # unit tests only
pytest tests/test_functional.py     # E2E subprocess tests
pytest tests/test_architecture.py   # architecture rules
pytest tests/test_pytest_plugin.py  # plugin integration via pytester
```

```bash
pytest tests/test_fixer.py           # fixer unit tests
pytest tests/test_fixer_integration.py # fixer integration tests
```

The `pytester` fixture (enabled via `conftest.py`) creates isolated pytest runs for plugin testing — each test gets its own temporary project with real component files.
