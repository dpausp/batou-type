# Quality Audit Report — 2026-04-24

## Human Summary
Quality meta-audit of batou-type project revealed solid fundamentals: zero mocking, real subprocess E2E tests, clean module separation. Two critical issues found and fixed: (1) README documented `basedpyright` as supported checker but the `Checker` enum only has `ty` and `mypy` — removed inaccurate docs, (2) two tests had stale string assertions after CLI output format changes — updated to match current output. Additional fixes: excluded `testproject/` from ruff (intentional bad fixtures), changed bare `print()` to `console.print()` in cli.py for consistency. Remaining gaps: pytest plugin has zero test coverage, `_run_check()` is a 56-statement god function, inverted test pyramid (all E2E, zero unit).

## Completion Checklist
- [x] Entry point inventory completed (all subcommands, scripts, APIs catalogued)
- [x] E2E smoke test completed (basic invocation tested)
- [x] All raw data collected in `.agents/tmp/quality/` (baseline/, extreme/, analysis/, e2e/)
- [x] All 4 investigation streams completed with structured review results
- [x] Tool tolerance audit produced with per-tool signals (ruff/ty/noqa)
- [x] Test structure report with mock health metrics
- [x] E2E coverage assessed for every entry point (PROVEN/SUSPECTED/UNKNOWN/BROKEN)
- [ ] Full CLI test executed: SKIPPED — evidence sufficient, no crash conditions requiring deeper investigation
- [x] Fixes applied for critical findings (2 stale tests, README docs mismatch, ruff config, print consistency)
- [x] Baseline re-run confirms no regressions
- [ ] Git commit: pending

## Entry Point Inventory

| Entry Point | Type | Source | E2E Status | Evidence |
|-------------|------|--------|------------|----------|
| batou-type check | CLI command | src/batou_type/cli.py:154 | PROVEN | 6 tests in test_functional.py::TestCheck + smoke test PASS |
| batou-type version | CLI command | src/batou_type/cli.py:57 | PROVEN | 2 tests + smoke test PASS |
| batou-type --help | CLI option | src/batou_type/cli.py:24 | PROVEN | test_help_shows_commands + smoke test PASS |
| python -m batou_type | Module entry | src/batou_type/__main__.py:1 | PROVEN | All tests use -m invocation |
| -c ty checker | CLI option | src/batou_type/core.py:39 | PROVEN | test_check_with_ty_checker |
| -c mypy checker | CLI option | src/batou_type/core.py:40 | SUSPECTED | test_check_with_mypy_checker accepts 0,1,2 — doesn't verify mypy runs |
| -c basedpyright checker | CLI option | REMOVED from README | N/A | Was documented but never implemented in Checker enum |
| --batou-ty pytest plugin | Pytest hook | src/batou_type/pytest_plugin.py:14 | UNKNOWN | Zero test coverage for 101-line plugin |
| Multi-checker sequential | CLI option | README.md | UNKNOWN | Documented but no test exercises -c ty -c mypy |
| Venv detection (.venv/appenv) | Feature | src/batou_type/core.py:13 | PROVEN | Smoke test detects testproject/.venv correctly |
| Migration testing | Documented feature | README.md | UNKNOWN | No test evidence |

## Tool Tolerance Audit

| Tool | Baseline | Extreme | Delta | Signal |
|------|----------|---------|-------|--------|
| ruff | 3 issues (testproject F841) → **0 post-fix** | ~120 issues (47 rule codes) | 117 suppressed | **green** |
| ty | 1 diagnostic (unresolved-attribute) | 1 diagnostic | 1 type:ignore (properly scoped) | **green** |

### Ruff Suppression Breakdown

- **Legitimate**: CPY001 (copyright), B008 (typer defaults), S101 (assert in tests), INP001 (test fixtures), D100-D107/ANN* in tests, S106/S404/S603 in test fixtures
- **Questionable**: BLE001 (blind except Exception in cli.py:50), I001 (import sorting 4 files), E501 (4 line-length violations), W391 (trailing newline)
- **Critical hiding**: C901+PLR0912+PLR0915 (_run_check complexity invisible in baseline)

## Test Structure

- Total tests: 27
- Distribution: unit 0, integration 15, e2e 12
- Mock health: 0 MagicMock, 0 with spec=, 0 with autospec=
- RED FLAGS: 2/10 — inverted pyramid (all E2E, zero unit), class-based tests without class state
- Signal: orange

## E2E Coverage Assessment

- PROVEN: 6 entry points (check, version, --help, python -m, -c ty, venv detection)
- SUSPECTED: 1 entry point (-c mypy checker — non-committal test)
- UNKNOWN: 2 entry points (--batou-ty pytest plugin, multi-checker)
- BROKEN: 0 entry points post-fix (basedpyright removed from docs, not a code break)
- Full CLI test triggered: NO
- Signal: orange (improved from red after fixing docs mismatch)

## Stream Signals

- Code Architecture: orange (no test_architecture.py, god function in _run_check)
- Code Quality: orange (117 suppressed ruff rules mostly legit, 1 questionable BLE001, complexity hidden)
- Test Structure: orange (zero mocks excellent, but inverted pyramid, pytest plugin untested)
- E2E Coverage + Production Reality: orange (core commands PROVEN, gaps in plugin and multi-checker)

## Critical Findings Fixed

1. **Stale test assertions** (tests/test_functional.py lines 55, 64): Updated to match current CLI output messages after format change
2. **README basedpyright mismatch** (README.md): Removed basedpyright documentation — Checker enum only supports ty and mypy
3. **Ruff config gap** (pyproject.toml): Added [tool.ruff] extend-exclude for testproject/ (intentional bad fixtures)
4. **Print inconsistency** (src/batou_type/cli.py:139): Changed bare print() to console.print() for output consistency

## Code Volume

| File | Change |
|------|--------|
| tests/test_functional.py | 2 assertions updated |
| README.md | Removed 4 lines (basedpyright references) |
| src/batou_type/cli.py | 1 line changed (print → console.print) |
| pyproject.toml | 2 lines added ([tool.ruff] config) |

## Post-Fix Quality Gates

| Tool | Result |
|------|--------|
| pytest | 27 passed |
| ruff | 0 issues |
| ty | 1 diagnostic (pre-existing, type:ignore present) |
| architecture | N/A (no test_architecture.py) |
| E2E smoke | PASS (all core commands working) |

## Recommendations

1. **HIGH**: Add tests for pytest_plugin.py — 101 lines of hook logic completely untested. The --batou-ty feature could be silently broken.
2. **MEDIUM**: Decompose _run_check() god function (56 statements, complexity 16). Extract stub display, project discovery, and result display into separate functions.
3. **MEDIUM**: Add unit tests for core.py functions (find_project_venv, get_venv_site_packages, check_file, check_all) — currently only tested via subprocess E2E.
4. **LOW**: Fix mypy checker test to verify mypy actually runs instead of accepting any exit code.
5. **LOW**: Add test exercising multi-checker mode (-c ty -c mypy).
6. **LOW**: Consider adding test_architecture.py with pytest-archon rules to enforce module boundaries.

## Raw Data Location

`.agents/tmp/quality/` — baseline/, extreme/, analysis/, e2e/
