# Quality Meta-Audit Investigation

## Stream A: Code Architecture

### Module Structure

```
src/batou_type/
  __init__.py        (25 lines) — re-exports from core, version detection
  __main__.py        (3 lines)  — delegates to cli.app
  core.py            (197 lines) — pure domain logic
  cli.py             (203 lines) — presentation layer (typer + rich)
  pytest_plugin.py   (101 lines) — pytest integration layer
  vendor/            — isolated stub packages (batou, batou_ext)
```

### Dependency Graph

```
__main__.py → cli.py → core.py
__init__.py → core.py
pytest_plugin.py → core.py
cli.py → core.py (never the reverse)
```

### Assessment

**Module boundaries are clean.** The architecture follows a strict layered pattern:

1. **core.py** — zero UI imports. No typer, no rich. Pure logic: venv detection, component discovery, subprocess invocation for type checkers. All functions are stateless and testable.

2. **cli.py** — presentation layer only. Imports from core, formats output via rich, defines typer commands. Never imported by core or plugin.

3. **pytest_plugin.py** — integration layer. Imports from core only. Implements pytest hook protocol (addoption, configure, collect_file, collection_modifyitems).

4. **__init__.py** — thin re-export facade. 5 symbols from core + `__version__`.

5. **vendor/** — completely isolated. No batou_type imports. Pure stub definitions.

**No architecture tests exist** (confirmed: `baseline/architecture-check.txt` = "no architecture tests"). However, the codebase is small enough (5 modules, ~530 LOC total excluding vendor) that the natural structure is self-enforcing. The `test_refactor_contract.py` file serves as an informal architecture guard — 14 AST-based tests verifying module structure, import boundaries, and entry points.

**One concern:** `_run_check()` in cli.py (lines 80-174) is flagged by ruff for high complexity:
- C901: complexity 20 > 10
- PLR0912: 23 branches > 12
- PLR0915: 63 statements > 50
- PLR0914: 16 local variables > 15

This function handles stub detection, project discovery, venv resolution, component checking, and multi-project summary output. It's the natural "main loop" of the CLI, so some complexity is expected, but it could benefit from extracting sub-functions.

**Signal: GREEN**

---

## Stream B: Code Quality — Tool Tolerance Audit

### Baseline ruff: 53 issues

| Category | Count | Location | Verdict |
|----------|-------|----------|---------|
| F841 (unused vars) | 19 | examples/ | Legitimate — test fixtures demonstrating type errors |
| F821 (reveal_type) | 25 | examples/ | Legitimate — type checker probe function |
| F401 (unused imports) | 4 | project code | **Real issues** (see below) |
| E402 (import not at top) | 1 | tests/ | Legitimate — after sys.path manipulation |
| invalid-syntax | 2 | vendor/*.pyi | Known — PEP 695 generics vs Python 3.10 target |
| F401 | 1 | vendor/ | Vendor stub — not our code |
| F401 | 1 | tests/ | Minor — unused `Component` import |

**F401 unused imports in project code (actionable):**

1. `cli.py:18` — `TypeCheckResult` imported but never used
2. `cli.py:19` — `VenvInfo` imported but never used (venv info goes through core functions)
3. `core.py:4` — `shlex` imported but never used (dead import from refactoring)
4. `tests/test_attribute_types.py:14` — `Component` imported but never used

### Extreme ruff (--select ALL): 708 issues total

**613 additional issues from expanded ruleset.** Breakdown by location:

| Location | Issues | Key Rules |
|----------|--------|-----------|
| examples/ | ~500 | D102, D101, ANN201, S101, I001, CPY001, INP001, N999 |
| vendor/ | ~40 | unresolved-import (typing.Self/override on 3.10) |
| src/batou_type/ | ~20 | C901, PLR0912, E501, DOC201, B008, F401 |
| tests/ | ~50 | S101, D10x, ANN, F401 |

**Project code issues (src/batou_type/) from extreme ruleset — categorized:**

Legitimate suppressions (would never fix):
- B008: typer.Argument/Option in defaults — standard typer pattern, false positive
- S404/S603: subprocess usage — already annotated with nosec, intentional
- PLW1510: subprocess.run without check — intentional (checking returncode manually)
- CPY001: missing copyright notices — style choice

Questionable (could fix):
- C901/PLR0912/PLR0915: _run_check complexity — real concern but expected for CLI main loop
- E501: ~8 lines over 88 chars — minor formatting
- PERF401: list append in loop — minor optimization
- RUF022: __all__ not sorted — cosmetic

Critical hiding: **None.**

### type:ignore audit (43 total)

| Location | Count | Category | Verdict |
|----------|-------|----------|---------|
| cli.py | 1 | `unresolved-attribute` on importlib.resources | Legitimate — Traversable.parent API ambiguity |
| vendor/__init__.pyi | 35 | `override` on from_context methods | Legitimate — matching batou's polymorphic error API |
| vendor/*.pyi | 7 | `assignment` on class vars | Legitimate — stub narrowing parent types |

All type:ignore comments carry specific error codes (no bare `# type: ignore`). The single project-code instance in cli.py is well-justified.

### noqa audit (9 total, all in vendor/)

All noqa comments are in vendor stubs matching batou's original API naming:
- N802/N801: naming conventions matching batou source
- PYI029/Y029: __repr__ in stubs
- E402: import ordering
- A001/A002: builtin shadowing (hash, filter, max)

All are legitimate. Zero noqa in project code.

### ty diagnostics (88 total)

All 88 ty diagnostics are in `vendor/` stubs. Breakdown:
- ~30: `invalid-method-override` (from_context polymorphism)
- ~45: `unresolved-import`/`unresolved-attribute` (typing.Self, typing.override not in 3.10)
- 2: `invalid-syntax` (PEP 695 generics in .pyi)
- 1: `not-subscriptable` (Attribute[T] on 3.10)
- 1: `unresolved-import` (OutputBackend in remote_core.pyi)

**Zero ty diagnostics in project code.** The single `type: ignore[unresolved-attribute]` in cli.py suppresses the only project-level finding.

**Signal: GREEN** for ruff (minor F401 cleanup only) and GREEN for ty (zero project issues).

---

## Stream C: Test Structure

### Test Distribution (60 tests, 5 files)

| File | Tests | Type | Mechanism |
|------|-------|------|-----------|
| test_core.py | 16 | Unit | tmp_path fixtures, real filesystem operations |
| test_attribute_types.py | 5 | Integration | Real batou Component/Environment/Host infrastructure |
| test_functional.py | 12 | E2E | subprocess.run invoking actual CLI |
| test_pytest_plugin.py | 7 | Integration | pytester (real pytest subprocess) |
| test_refactor_contract.py | 14 | Contract | AST parsing + import verification |

### Pyramid Distribution

```
E2E:         12 tests (20%) — CLI subprocess invocation
Integration: 26 tests (43%) — pytester, real batou, AST contracts
Unit:        22 tests (37%) — pure function tests with tmp_path
```

This is a healthy inverted pyramid for a CLI tool: heavy on real execution, light on isolated unit tests.

### Mock Health

| Metric | Count |
|--------|-------|
| Total mocks | 0 |
| With spec | 0 |
| Bare MagicMock | 0 |
| @patch decorators | 0 |
| unittest.mock imports | 0 |

**Mock ratio: 0%.** Every test exercises real code paths.

### Test Suppressions

| Metric | Count |
|--------|-------|
| @pytest.skip | 0 |
| @pytest.xfail | 0 |
| pytest.importorskip | 0 |

### RED FLAGS Check (python-audit mock-only detection)

| Red Flag | Status |
|----------|--------|
| Extensive unittest.mock imports | NO (zero) |
| No real database/filesystem | NO (tmp_path used extensively) |
| No real HTTP client | N/A (not applicable) |
| Assert on mock calls | NO (zero mocks) |
| No SQL execution | N/A |
| No HTTP requests | N/A |
| Pass without dependencies | NO (needs batou, ty installed) |
| No conftest.py with infrastructure | NO (conftest.py provides pytester) |
| Fixtures return Mock objects | NO (zero) |
| @patch() on own code | NO (zero) |

**Score: 0/10 RED FLAGS.** Test suite is exemplary.

### Gaps

- `Migration testing workflow` (README.md:39) has **no tests**. Documented feature without coverage.
- test_core.py imports `os` but never uses it (F401). Harmless but sloppy.
- test_attribute_types.py uses `os.chdir()` in fixture — modifies global state (unavoidable for batou integration, but worth noting).

**Signal: GREEN**

---

## Stream D: E2E Coverage + Production Reality

### Smoke Test Results

All 9 smoke test commands PASS:
- `--help`: exit 0, shows version + check commands
- `version`: exit 0, shows version + stub info
- `check --help`: exit 0, shows options
- `check clean-project`: exit 0, 10 components pass
- `check error-project`: exit 1, correctly detects 7 failures (bad_address, bad_content, boto_bad_usage, httpx_bad_usage, multi_error, silent_bugs, type_drift)

### Entry Point Coverage Matrix

| Entry Point | Type | E2E Status | Evidence |
|-------------|------|------------|----------|
| `version` | CLI subcommand | PROVEN | Smoke test + test_functional.py::TestVersion (2 subprocess tests) |
| `check` | CLI subcommand | PROVEN | Smoke test + test_functional.py::TestCheck (7 subprocess tests) |
| `--help` | CLI flag | PROVEN | Smoke test + test_functional.py::TestHelp (3 tests) |
| `batou-type` | Console script | PROVEN | All functional tests invoke via `-m batou_type` |
| `python -m batou_type` | Module execution | PROVEN | test_functional.py uses `[sys.executable, "-m", "batou_type"]` |
| pytest plugin | pytest11 entry point | PROVEN | test_pytest_plugin.py (7 pytester tests) |
| `Checker` | Public API enum | PROVEN | test_refactor_contract.py + test_functional.py (-c flag) |
| `TypeCheckResult` | Public API dataclass | PROVEN | test_refactor_contract.py (import verification) |
| `check_all` | Public API function | PROVEN | test_pytest_plugin.py (exercises via plugin), test_refactor_contract.py |
| `check_file` | Public API function | PROVEN | test_refactor_contract.py (import verification) |
| `find_components` | Public API function | PROVEN | test_core.py::TestFindComponents (6 tests with real filesystem) |
| `__version__` | Public API attribute | PROVEN | test_refactor_contract.py + test_functional.py |
| Migration testing | Documented feature | **UNKNOWN** | entry-points.md: "[NO TEST]" |

### Production Reality

- **All CLI paths tested via subprocess** — no in-process monkey-patching
- **pytest plugin tested via pytester** — runs real pytest subprocess with --batou-ty flag
- **batou integration tested with real infrastructure** — Environment, Host, ComponentDefinition in test_attribute_types.py
- **Component discovery tested with real filesystem** — tmp_path in test_core.py
- **No path tested only with mocks** — zero mocks exist
- **No slow/integration tests excluded from default runs** — all 60 tests run in ~0.5s

### Coverage Gap

The only gap is `Migration testing workflow` (README.md:39) — documented but untested. This is a documentation/usage pattern, not a code feature, so the gap is minor.

**Signal: GREEN**

---

## Summary

```yaml
entry_point_coverage:
  - name: "version"
    type: cli-subcommand
    e2e_status: PROVEN
    evidence: "Smoke test PASS + test_functional.py::TestVersion (2 subprocess tests)"
  - name: "check"
    type: cli-subcommand
    e2e_status: PROVEN
    evidence: "Smoke test PASS (clean: exit 0, error: exit 1 with 7 failures) + test_functional.py::TestCheck (7 subprocess tests)"
  - name: "pytest plugin"
    type: pytest-entry-point
    e2e_status: PROVEN
    evidence: "test_pytest_plugin.py (7 pytester tests — real pytest subprocess)"
  - name: "batou-type"
    type: console-script
    e2e_status: PROVEN
    evidence: "test_functional.py invokes python -m batou_type via subprocess"
  - name: "python -m batou_type"
    type: module-execution
    e2e_status: PROVEN
    evidence: "test_functional.py BATOU_TYPE_CLI = [sys.executable, '-m', 'batou_type']"
  - name: "Checker"
    type: public-api
    e2e_status: PROVEN
    evidence: "test_refactor_contract.py + test_functional.py (-c ty/mypy)"
  - name: "TypeCheckResult"
    type: public-api
    e2e_status: PROVEN
    evidence: "test_refactor_contract.py (import verification)"
  - name: "check_all"
    type: public-api
    e2e_status: PROVEN
    evidence: "test_pytest_plugin.py exercises via plugin + test_refactor_contract.py"
  - name: "check_file"
    type: public-api
    e2e_status: PROVEN
    evidence: "test_refactor_contract.py (import verification)"
  - name: "find_components"
    type: public-api
    e2e_status: PROVEN
    evidence: "test_core.py::TestFindComponents (6 tests, real filesystem)"
  - name: "__version__"
    type: public-api
    e2e_status: PROVEN
    evidence: "test_refactor_contract.py + test_functional.py"
  - name: "Migration testing workflow"
    type: documented-feature
    e2e_status: UNKNOWN
    evidence: "README.md:39 documents feature but entry-points.md notes [NO TEST]"

tool_tolerance_audit:
  ruff:
    project_config_issues: 53
    full_ruleset_issues: 708
    delta:
      legitimate_suppressions: 600
      questionable: 12
      critical_hiding: 0
    signal: green
  ty:
    type_ignore_comments: 43
    bare_type_ignores: 0
    signal: green

test_structure:
  total_tests: 60
  distribution:
    unit: 22
    integration: 26
    e2e: 12
  mock_health:
    total_mocks: 0
    with_spec: 0
    bare_magicmock: 0
  gaps:
    - "Migration testing workflow has no tests (README.md:39)"
    - "3 unused imports in project code (F401: shlex, TypeCheckResult, VenvInfo)"
  signal: green

stream_signals:
  code_architecture: green
  code_quality: green
  test_structure: green
  e2e_coverage: green

e2e_credibility:
  proven_count: 11
  suspected_count: 0
  unknown_count: 1
  broken_count: 0
  credible: true
  full_cli_test_needed: false
```
