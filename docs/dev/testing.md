# Testing

The test suite validates correctness, architecture, and the public API contract — without any mocks.

## Test Pyramid

```
       ┌──────────┐
       │  E2E  18 │  14% — subprocess CLI invocation
       ├──────────┤
       │ Integ  45 │  34% — pytester plugin tests, AST contract tests
       ├──────────┤
       │ Unit  69 │  52% — pure functions, logging events, output models, architecture rules
       └──────────┘
```

The 132 tests have a **0% mock ratio** — no `MagicMock`, no `patch`, no test doubles. Every test exercises real code paths: unit tests hit real filesystem via `tmp_path`, integration tests run the real pytest plugin via `pytester`, and E2E tests spawn real subprocesses.

## Test Files and Their Role

| File | Role |
|------|------|
| `test_core.py` | Unit tests for path detection and component discovery with `tmp_path` |
| `test_pytest_plugin.py` | Integration tests via `pytester` — creates real component files, runs `--batou-ty` |
| `test_functional.py` | E2E tests — spawns `python -m batou_type` as subprocess, asserts on exit codes and output |
| `test_logging.py` | In-process logging event tests — calls `run_check()` directly, asserts on structured events via `capture_logs` |
| `test_output.py` | Unit tests for Pydantic output models, JSON serialization, and schema export |
| `test_architecture.py` | Architecture enforcement via `pytest-archon` import rules |
| `test_refactor_contract.py` | AST-based structural contracts (module existence, import boundaries, public API) |
| `test_attribute_types.py` | Attribute type correctness in vendor stubs |

## Architecture Enforcement

`test_architecture.py` uses `pytest-archon` to enforce the layered structure at import level:

- **Core purity** — `core.py` must not import typer, rich, pytest, or any other `batou_type` module.
- **Framework isolation** — typer and rich are banned outside `cli.py`; pytest is banned outside `pytest_plugin.py`; `__init__.py` must not import either framework directly.
- **Cross-layer isolation** — CLI and plugin must not import each other; `__main__.py` may only import from `cli.py`.
- **Init purity** — `__init__.py` must only import from `core.py`, never from `cli.py` or `pytest_plugin.py`.

These rules are negative constraints ("must not import X") checked against the actual import graph, not convention. They make accidental layer violations fail at CI time.

## Coverage Characteristics

Measured coverage does not tell the full story because E2E tests invoke the CLI as a subprocess — coverage tooling does not instrument the child process.

### Coverage Tiers

| Tier | Modules | What this means |
|------|---------|-----------------|
| **Well-tested** | `core.py`, `pytest_plugin.py` | Directly imported by unit and integration tests. Measured coverage reflects real usage. |
| **Functionally tested + in-process logging** | `cli.py` | 18 E2E subprocess tests exercise every subcommand and flag. 16 in-process logging tests cover all structured events via `capture_logs`. E2E subprocess coverage is not measured; in-process coverage is. |
| **Trivial** | `__init__.py`, `__main__.py` | Re-exports and a two-line trampoline. Version-fallback logging covered by contract tests. |

`cli.py` has two complementary test layers: E2E subprocess tests assert on exit codes, stdout, and stderr for integration coverage; in-process logging tests call `run_check()` directly and assert on structured events via `structlog.testing.capture_logs`. The logging tests cover every event ID in the event catalog.

## Running Tests

```bash
pytest                              # full suite
pytest tests/test_core.py           # unit tests only
pytest tests/test_functional.py     # E2E subprocess tests
pytest tests/test_logging.py        # in-process logging event tests
pytest tests/test_architecture.py   # architecture rules
pytest tests/test_pytest_plugin.py  # plugin integration via pytester
```

The `pytester` fixture (enabled via `conftest.py`) creates isolated pytest runs for plugin testing — each test gets its own temporary project with real component files.
