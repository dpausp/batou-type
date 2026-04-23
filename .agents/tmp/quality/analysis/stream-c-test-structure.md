# Stream C: Test Structure

## Verdict: RED

## Test Inventory

**1 test file, 14 tests total:**

All tests live in `tests/test_refactor_contract.py`. There are no other test files.

```
tests/test_refactor_contract.py::test_cli_module_exists
tests/test_refactor_contract.py::test_cli_module_has_typer_app
tests/test_refactor_contract.py::test_init_no_typer_import
tests/test_refactor_contract.py::test_init_no_rich_import
tests/test_refactor_contract.py::test_init_exports_version
tests/test_refactor_contract.py::test_main_imports_from_cli
tests/test_refactor_contract.py::test_pyproject_entry_point_uses_cli
tests/test_refactor_contract.py::test_core_no_lazy_json_import
tests/test_refactor_contract.py::test_core_no_lazy_io_import
tests/test_refactor_contract.py::test_plugin_no_batou_ty_error
tests/test_refactor_contract.py::test_init_no_bare_except_exception
tests/test_refactor_contract.py::test_core_imports_still_work
tests/test_refactor_contract.py::test_cli_imports_work
tests/test_refactor_contract.py::test_init_reexports_core
```

## Test Classification

Every single test is a **structural/architectural contract test** — they parse AST, check file existence, verify import structure. None of them exercise runtime behavior.

| Category | Count | Tests |
|---|---|---|
| File/structure existence | 2 | `test_cli_module_exists`, `test_pyproject_entry_point_uses_cli` |
| AST shape checks (no forbidden imports) | 5 | `test_init_no_typer_import`, `test_init_no_rich_import`, `test_core_no_lazy_json_import`, `test_core_no_lazy_io_import`, `test_init_no_bare_except_exception` |
| AST shape checks (must contain) | 3 | `test_cli_module_has_typer_app`, `test_init_exports_version`, `test_plugin_no_batou_ty_error` |
| Import smoke tests | 4 | `test_core_imports_still_work`, `test_cli_imports_work`, `test_init_reexports_core`, `test_main_imports_from_cli` |

## What Is NOT Tested

**Zero functional tests.** The following behaviors have NO test coverage:

1. **`check_file()`** — No test runs subprocess type checking and validates output
2. **`check_all()`** — No test verifies multi-file type checking
3. **`find_components()`** — No test with real filesystem components/ directory
4. **`_filter_basedpyright_json()`** — No test with real basedpyright JSON output
5. **CLI `check` command** — No test invokes the CLI and validates exit codes
6. **CLI `version` command** — No test validates version output format
7. **`get_stub_versions()`** — No test for stub version collection
8. **Pytest plugin** — No test exercises `--batou-ty` flag or `batou_ty` marker
9. **Exit code behavior** — No test verifies exit 0 (success) / exit 1 (errors)
10. **Error output format** — No test validates Rich-formatted error display

## Mock Analysis

- **mock-usage.txt**: Empty — zero mock patterns
- **mock-spec-usage.txt**: Empty — zero spec'd mocks
- **Mock ratio**: 0/0 = N/A (no mocks, but also no integration tests)

This is actually worse than high mock ratio. There are no mocks because **there are no tests that exercise code paths**. The tests don't even import the functions they're "testing" — they parse source files as text.

## Test Suppressions

**Zero** — no skip/xfail/skipif markers.

## Layer Coverage Map

| Source Module | Has Tests? | Test Type |
|---|---|---|
| `core.py` (149 lines) | Partial | AST structure checks only; import smoke test |
| `cli.py` (114 lines) | Partial | File existence + AST shape; import smoke test |
| `pytest_plugin.py` (101 lines) | Minimal | Only checks `BatouTyError` class removed |
| `__init__.py` (25 lines) | Partial | Import structure checks |
| `__main__.py` (3 lines) | Yes | Import target check |

## Python-Audit RED FLAGS Checklist

| Flag | Status | Evidence |
|---|---|---|
| Every test file imports `unittest.mock` extensively | NO | No mocks at all |
| No test uses real subprocess | **YES** | `core.py` runs subprocess — no test exercises this |
| Tests assert on mock calls rather than state | NO | No mocks |
| Suite would pass if dependencies uninstalled | **YES** | Tests only parse AST and check imports; would pass without `rich`, `typer`, `subprocess` working |
| No conftest.py sets up real infrastructure | **YES** | No `conftest.py` exists |
| Tests use `@patch()` on SUT imports | NO | No patches |
| No integration test directory | **YES** | Only one flat test file |

**RED FLAGS hit: 3** (no real subprocess, suite passes without deps, no conftest/infrastructure). However, the pattern is different from classic "mock-only" — this is "AST-only." The tests verify code structure, not behavior. They provide **zero confidence** that the application actually works.

## Test Structure Violations

- **No conftest.py at all** — every test file sets up its own fixtures (the `SRC` path is hardcoded at module level)
- **Fixture definitions in test files** — `SRC = Path(...)` is a module-level constant, not a fixture
- **Flat tests/ with no tier separation** — no unit/integration/e2e directories
- **No `import_mode = "importlib"`** in pytest config (no pytest config at all)

## Critical Gap Analysis

The test suite validates that the **refactoring was done correctly** (module renamed from `batou_typecheck` to `batou_type`, CLI extracted, imports cleaned up). It does NOT validate that the **application works**. The entire test file is named `test_refactor_contract.py` — it's a one-time migration guard, not an ongoing test suite.
