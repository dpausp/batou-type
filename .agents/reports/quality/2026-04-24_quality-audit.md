# Quality Audit Report — 2026-04-24

## Human Summary

The quality meta-audit of batou-type found one broken entry point (basedpyright subprocess crash due to missing `sys.executable -m` invocation) and fixed it. The test suite consists entirely of structural contract tests — zero functional tests exist. The core value proposition (running type checkers on batou components) has no automated test coverage. Ruff runs on zero configuration, hiding 84 issues including blind exception catches and missing annotations. Architecture is clean by convention but not enforced.

## Completion Checklist

- [x] Entry point inventory completed (all subcommands, scripts, APIs catalogued)
- [x] E2E smoke test completed (basic invocation tested)
- [x] All raw data collected in `.agents/tmp/quality/` (baseline/, extreme/, analysis/, e2e/)
- [x] All 4 investigation streams completed with structured review results
- [x] Tool tolerance audit produced with per-tool signals (ruff/ty/noqa)
- [x] Test structure report with mock health metrics
- [x] E2E coverage assessed for every entry point (PROVEN/SUSPECTED/UNKNOWN/BROKEN)
- [x] Full CLI test executed (triggered by synthesis — 62% UNKNOWN entry points)
- [x] Fixes applied for critical findings (basedpyright subprocess invocation)
- [x] Baseline re-run confirms no regressions
- [x] Git commit: pending on branch main

## Entry Point Inventory

| Entry Point | Type | Source | E2E Status | Evidence |
|-------------|------|--------|------------|----------|
| version | cli-subcommand | src/batou_type/cli.py:48 | PROVEN | E2E: exit 0, correct output |
| check --help | cli-subcommand | src/batou_type/cli.py:104 | PROVEN | E2E: exit 0 |
| check (no components) | cli-subcommand | src/batou_type/cli.py:104 | PROVEN | E2E: exit 0, graceful message |
| check (with components, ty) | cli-subcommand | src/batou_type/core.py:47 | PROVEN | Full CLI test: exit 0/1 |
| check (with components, mypy) | cli-subcommand | src/batou_type/core.py:47 | PROVEN | Full CLI test: exit 0/1 |
| check (with components, basedpyright) | cli-subcommand | src/batou_type/core.py:47 | PROVEN (post-fix) | Full CLI test: was BROKEN, fixed |
| check exit codes | behavior | src/batou_type/cli.py:101 | PROVEN | Full CLI test verified exit 0 and exit 1 |
| pytest plugin --batou-ty | pytest-plugin | src/batou_type/pytest_plugin.py:16 | UNKNOWN | Zero test coverage, never exercised |
| check_all() / check_file() | public-api | src/batou_type/core.py:47,96 | UNKNOWN | Core execution path, only proven via CLI invocation |
| python -m batou_type | entry-point | src/batou_type/__main__.py | PROVEN | E2E: all tests used this invocation |

## Tool Tolerance Audit

| Tool | Baseline | Extreme | Delta | Signal |
|------|----------|---------|-------|--------|
| ruff | 0 issues (defaults only) | **84 issues** | **+84 suppressed** | orange |
| ty | 0 errors | 0 errors | 0 | green |
| noqa density | 0 | 0 | 0 | green |
| type:ignore | 1 (scoped) | 1 | 0 | green |

### Ruff Suppression Breakdown

- **Legitimate** (~39): CPY001 (5), S101 in tests (14), D-rules (9), DOC201/DOC501 (6), COM812 (3), RUF022 (1), RUF067 (1)
- **Questionable** (~20): E501 (2), PLW1510 (2), BLE001 (1), PERF203 (1), ANN (7+), PLC0415 (2), I001 (1), RUF100 (4)
- **Critical Hiding** (~4): S404 (1), S603 (2), B008 (1)

### Key Issue: Zero Ruff Configuration

The project has **no `[tool.ruff]` section** in pyproject.toml, no `.ruff.toml`, no `ruff.toml`. Running on pure defaults means most quality rules are silently skipped. Notable gaps: no line length enforcement, no annotation requirements, no security rule awareness.

## Test Structure

- **Total tests**: 14
- **Distribution**: structural/AST: 14, unit: 0, integration: 0, e2e: 0
- **Mock health**: 0 MagicMock, 0 with spec=, 0 with autospec= (N/A — no mocks because no functional tests)
- **RED FLAGS**: 3/10 — no real subprocess testing, suite passes without dependencies, no conftest/infrastructure
- **Signal**: red

### Test Gap Summary

All 14 tests are in `test_refactor_contract.py` — a one-time migration guard verifying module structure. The following behaviors have **zero test coverage**:

1. `check_file()` — subprocess invocation against real type checkers
2. `check_all()` — multi-file type checking
3. `find_components()` — real filesystem component discovery
4. `_filter_basedpyright_json()` — JSON parsing and filtering
5. CLI `check` command — exit codes, output format
6. CLI `version` command — output format
7. `get_stub_versions()` — stub version collection
8. Pytest plugin — collection, --batou-ty flag, batou_ty marker
9. Exit code semantics (0 = success, 1 = errors)
10. Error output format (Rich-formatted display)

## E2E Coverage Assessment

- **PROVEN**: 7 entry points (version, check basic/ty/mypy/basedpyright, exit codes, python -m)
- **UNKNOWN**: 2 entry points (pytest plugin, check_all/check_file library API)
- **BROKEN**: 0 (basedpyright was broken, now fixed)
- **Full CLI test triggered**: YES — 62% UNKNOWN triggered systematic testing
- **Signal**: orange

## Stream Signals

- Code Architecture: **red** — no architecture tests, no pytest-archon, convention-only enforcement
- Code Quality: **orange** — zero ruff config, 84 suppressed issues, 1 scoped type:ignore, ty clean
- Test Structure: **red** — zero functional tests, AST-only contract tests, 3 RED FLAGS
- E2E Coverage + Production Reality: **orange** — smoke tests pass, core value untested in automation

## Critical Findings Fixed

### BUG-1: basedpyright FileNotFoundError (severity: HIGH)

**Root cause**: `core.py:71` used bare `["basedpyright", "--outputjson"]` for subprocess invocation while ty and mypy used `sys.executable -m`. When venv isn't activated, `basedpyright` isn't on PATH.

**Fix**: Changed to explicit `elif c == Checker.basedpyright:` branch using `[sys.executable, "-m", "basedpyright", *CHECKER_COMMANDS[c][1:], file_path]`.

**File**: `src/batou_type/core.py` lines 70-71 → new explicit branch

## Code Volume

| File | Change |
|------|--------|
| src/batou_type/core.py | +2 lines (explicit basedpyright branch with sys.executable) |

## Post-Fix Quality Gates

| Tool | Result |
|------|--------|
| pytest | 14 passed |
| ruff | 0 issues |
| ty | 0 errors |
| architecture | N/A (no test_architecture.py) |
| E2E smoke (all commands) | PASS |
| E2E basedpyright (post-fix) | PASS |

## Recommendations

### High Priority

1. **Add functional tests** — at minimum: `check_file()` with mock subprocess, `find_components()` with temp directory, `_filter_basedpyright_json()` with sample JSON, exit code verification via `subprocess.run` of the CLI
2. **Add ruff configuration** — select at minimum: E, W, F, I, UP, ANN, S, BLE, PL, RUF. This would have caught the basedpyright bug at lint time (PLW1510 flags subprocess.run without check=)
3. **Add pytest-archon rules** — enforce that `core.py` never imports from `cli.py` or `pytest_plugin.py`, that `cli.py` imports from `core.py` only

### Medium Priority

4. **Narrow `except Exception`** in `cli.py:41` (`get_stub_versions()`) to `PackageNotFoundError` — currently silently swallows all errors
5. **Fix README naming** — README uses `batou-typecheck` everywhere, actual command is `batou-type`
6. **Document `version` subcommand and pytest plugin** in README
7. **Fix stale `.gitignore`** — references `src/batou_typecheck/` (old package name)
8. **Add `conftest.py`** with shared fixtures (SRC path, temp components directory)
9. **Add `[tool.pytest.ini_options]`** with `import_mode = "importlib"`

### Low Priority

10. **Add copyright headers** (CPY001) or add to ruff ignore list as explicit decision
11. **Add return type annotations** (ANN201) to all public functions
12. **Add D-rules** to ruff config or add to ignore list as explicit decision

## Raw Data Location

`.agents/tmp/quality/` — baseline/, extreme/, analysis/, e2e/
