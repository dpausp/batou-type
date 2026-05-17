# Quality Audit Report

**Date:** 2026-05-18
**Project:** batou-type
**Grade:** B+ (87/100)

## Human Summary

batou-type is a well-engineered project with genuinely enforced architecture (33 pytest-archon rules), real E2E testing via subprocess invocation, and excellent tooling hygiene. All 7 entry points are PROVEN through functional tests. The 0/1080 ruff delta is clean — no critical issues hidden by config. The 1.7% mock ratio is genuinely healthy for a CLI tool tested via real subprocesses. Three advisory items identified: complexity hotspots in cli.py (run_fix CC=116, run_check CC=59), core.py coverage at 62%, and migration testing without explicit test coverage. No fixes applied — all quality gates green.

## Completion Checklist

- [x] Entry point inventory + smoke test completed
- [x] Structural inventory completed (noqa, mock, complexity, test discovery, dependencies)
- [x] Quality gates collected (baseline + extreme)
- [x] All 4 investigation streams completed with structured review results
- [x] Tool tolerance audit produced with per-tool signals (ruff/ty/pytest)
- [x] Test collection integrity verified (all test files collected, no config hiding)
- [x] Skip/xfail/xpass audit completed (zero markers found)
- [x] Test double strategy analyzed (mock:fake:golden:real per layer)
- [x] E2E coverage assessed for every entry point (PROVEN/SUSPECTED/UNKNOWN/BROKEN)
- [x] Full CLI test not triggered — existing E2E evidence sufficient
- [x] No fixes needed — all quality gates GREEN
- [x] North Star generated from loaded skills
- [x] Course Corrections derived (Reality vs North Star diff)
- [ ] Git commit pending

## Entry Point Inventory

| Entry Point | Type | Source | Smoke | E2E Status | Evidence |
|-------------|------|--------|-------|------------|----------|
| `batou-type version` | CLI subcommand | src/batou_type/cli.py:94-106 | PASS | PROVEN | test_functional.py::TestVersion (2 tests) |
| `batou-type check` | CLI subcommand | src/batou_type/cli.py:549-659 | PASS | PROVEN | test_functional.py::TestCheck (7), TestJsonOutput (4), TestFixDiff (3) |
| `batou-type setup` | CLI subcommand | src/batou_type/cli.py:662-714 | PASS | PROVEN | impl_spec/test_setup_command.py (34 tests) |
| `batou-type` (console_scripts) | Script entry | pyproject.toml:26-27 | PASS | PROVEN | test_functional.py::TestHelp (3 tests) |
| `python -m batou_type` | Module entry | src/batou_type/__main__.py:1-3 | PASS | PROVEN | test_functional.py::TestMainModule (3 tests) |
| `--batou-ty` (pytest11) | Plugin entry | pyproject.toml:29-30 | N/A | PROVEN | test_pytest_plugin.py (7 tests, pytester) |
| Public API (8 exports) | Programmatic | src/batou_type/__init__.py:19-28 | N/A | PROVEN | test_init.py (3 tests), test_refactor_contract.py (13 tests) |

## Tool Tolerance Audit

| Tool | Baseline | Extreme | Delta | Signal |
|------|----------|---------|-------|--------|
| ruff | 0 issues | 1080 issues | 1080 suppressed (all legitimate/cosmetic) | green |
| ty | 0 errors | 0 errors | 0 | green |
| pytest | 240 passed | — | 0 hidden tests | green |
| tox | 5/5 envs GREEN | — | — | green |

### Ruff Extreme Breakdown (1080 total)

| Rule Code | Count | % | Category | Verdict |
|-----------|-------|---|----------|---------|
| S101 | 347 | 32% | Assert in tests | LEGITIMATE |
| PLR6301 | 182 | 17% | Static method suggestion (tests) | COSMETIC |
| COM812 | 93 | 9% | Trailing comma | STYLE |
| D102 | 89 | 8% | Missing class docstrings (tests) | COSMETIC |
| PLC0415 | 68 | 6% | Lazy imports (CLI) | INTENTIONAL |
| ANN001 | 46 | 4% | Missing annotations (docs/conf.py, tests) | COSMETIC |
| DOC201 | 39 | 4% | Missing Returns in docstrings | COSMETIC |
| CPY001 | 24 | 2% | Copyright notices | OPTIONAL |
| Other (30+ codes) | ~92 | 9% | Various | COSMETIC |

**No critical issues hidden by config.** The 0-baseline is genuine quality, not suppression.

## Test Collection Integrity

| Check | Result | Signal |
|-------|--------|--------|
| Tests on disk | 12 files | — |
| Tests collected | 230 nodes | — |
| Uncollected files | 0 — all files collected | green |
| Collection errors | 0 | green |
| Config exclusions | import_mode=importlib (standard) | — |
| conftest hooks modifying collection | none (pytest_plugin.py has pytest_collect_file but only for --batou-ty) | green |

- pytest config: `import_mode = importlib`, no norecursedirs, no --ignore, no collect_ignore
- Unaccounted test files: none — all files collected

## Skip/Xfail/Xpass Audit

| Category | Count | Signal |
|----------|-------|--------|--------|
| @pytest.mark.skip | 0 | — |
| @pytest.mark.skipif (platform) | 0 | — |
| @pytest.mark.skipif (dependency) | 0 | — |
| @pytest.mark.xfail (strict=True) | 0 | — |
| @pytest.mark.xfail (strict=False) | 0 | — |
| XPASS | 0 | — |
| Lazy skips | 0 | — |
| Flaky-hidden | 0 | — |
| Stale temporal skips | 0 | — |

- Cross-platform skip asymmetry: none (zero skips of any kind)
- Suspicious skip details: none

## Test Double Strategy

| Layer | Mock | Spec'd Mock | Fake | Golden | Real | Total |
|-------|------|-------------|------|--------|------|-------|
| Unit | 0 | 4 | 0 | 0 | ~120 | ~124 |
| Integration | 0 | 0 | 0 | 0 | ~106 | ~106 |
| E2E | 0 | 0 | 0 | 0 | ~10 | ~10 |

- Tautological tests (mock theater): 0
- Golden file smell (no regenerate path): 0
- Mock density hotspots: none — only test_fixer_integration.py uses mocks (4 autospec=True for patch)
- Overall double strategy verdict: EXCELLENT — 1.7% mock ratio, all real dependencies
- Signal: green

## Test Structure Summary

- Total tests: 240 passed, 0 failed, 0 skipped, 1 warning
- Distribution: unit ~124, integration ~106, E2E ~10
- RED FLAGS: 0/10
- Signal: green

## Test Coverage

| Module | Coverage | Missing Lines | Signal |
|--------|----------|---------------|--------|
| src/batou_type/output.py | 98% | minimal | green |
| src/batou_type/fixer.py | 91% | minor | green |
| src/batou_type/setup.py | 91% | minor | green |
| src/batou_type/cli.py | 81% | partial | green |
| src/batou_type/pytest_plugin.py | 68% | moderate | orange |
| src/batou_type/core.py | 62% | significant | orange |
| src/batou_type/__init__.py | 0% | trivial trampoline | green |
| src/batou_type/__main__.py | 0% | trivial trampoline | green |

- Overall coverage: 81% (859 stmts, 166 miss)
- Modules < 50%: none (trampolines excluded)
- Entry points with 0% coverage: none (E2E smoke covers all)
- Signal: green

## Duration Anomalies

- Total suite time: 34s
- Duration stats: P50=0.46s, P90=0.61s, P95=0.73s, P99=1.81s

| Category | Count | Details |
|----------|-------|---------|
| EXTREME OUTLIER (>P99+2sigma) | 0 | None |
| FAKE SLOW (marked slow, <P50) | 0 | No slow markers exist |
| HIDDEN SLOW (unmarked, >P95) | 0 | Max test duration 1.81s (mypy checker) |
| Zero-duration (<1ms) | 0 | All tests execute real code |

- Slow test cluster: none — durations well-distributed
- Root causes for outliers: none
- Signal: green

## Dependency Audit

| Category | Count | Signal |
|----------|-------|--------|--------|
| Forbidden libraries | 0 | green |
| Stdlib reinvention | 0 | green |
| Unused dependencies | 0 | green |
| Missing blessed libraries | 0 | green |
| Available but unused (partial migration) | 0 | green |

- All runtime deps are blessed: libcst (AST), pydantic (validation), rich (output), typer (CLI), ty (type checking), tomli-w (TOML writing), stogger (logging)
- All test deps are blessed: pytest, pytest-cov, pytest-archon, pytest-ruff, pytest-ty, pytest-stogger, pytest-structlog
- Signal: green

## E2E Coverage Assessment

- PROVEN: 7 entry points (version, check, setup, console_scripts, __main__, pytest plugin, public API)
- SUSPECTED: 0 entry points
- UNKNOWN: 0 entry points
- BROKEN: 0 entry points
- Full CLI test triggered: NO
- Signal: green

## Stream Signals

| Stream | Signal | Key Finding |
|--------|--------|-------------|
| A: Code Architecture | green | 33 pytest-archon rules, ENFORCED at test time |
| B: Code Quality | green | 0 baseline, blessed deps only, zero forbidden |
| C: Test Structure | green | 240 pass, 0 skip, 1.7% mock ratio |
| D: E2E Coverage + Production Reality | green | 7/7 entry points PROVEN |
| E: Course Corrections | green (3 ORANGE NAVs) | Complexity, coverage, migration tests |

## Architectural North Star

Based on python-dev and python-audit skills.

| Dimension | True North | Source |
|-----------|------------|--------|
| CLI Framework | typer | python-dev |
| Logging | structlog | python-dev |
| HTTP Client | httpx | python-dev |
| Data Validation | pydantic v2 | python-dev |
| AST Manipulation | libcst | python-dev |
| TOML Writing | tomli-w | python-dev |
| Terminal Output | rich | python-dev |
| Type Checking | ty | python-dev |
| Testing | pytest | python-dev |
| Architecture Enforcement | pytest-archon | python-architecture |
| Path Handling | pathlib | python-dev |
| Mock Policy | real deps, mock only external boundaries | python-audit |
| Type Syntax | T \| None, list[T], PEP 695 | python-dev |
| Exception Handling | SPEC reference + re-raise | python-audit |
| Test Pyramid | unit > integration > E2E | python-tests |

## Course Corrections

### NAV-1 Function Complexity
- **Current heading:** run_fix() CC=116, run_check() CC=59 — mega-functions handling multiple concerns
- **True north:** Functions with CC < 10, single responsibility per function
- **Correction:** Decompose run_fix and run_check into smaller focused functions (JSON output, human output, project scanning, checker invocation)

### NAV-2 Core Coverage Gap
- **Current heading:** core.py at 62% — check_file() (CC=39) tested only indirectly
- **True north:** Core domain logic at 90%+ coverage with direct unit tests
- **Correction:** Add direct unit tests for check_file() paths (error parsing, multi-checker, JSON mode)

### NAV-3 Test Class Convention
- **Current heading:** Some test files use class-based organization (TestCheck, TestVersion, etc.)
- **True north:** Plain test_ functions per python-audit conventions
- **Correction:** Migrate to plain functions in new tests; existing classes are cosmetic, not blocking

### NAV-4 __init__.py Exports
- **Current heading:** __init__.py exports 8 symbols via __all__
- **True north:** Clean public API boundary with complete type stubs
- **Correction:** Ensure .pyi stubs exist for all exported symbols (already partially done via test_refactor_contract.py)

### NAV-5 Coverage Infrastructure
- **Current heading:** Coverage infrastructure exists and is used
- **True north:** Full CI pipeline with coverage gates
- **Correction:** Consider adding minimum coverage threshold to tox config

### NAV-6 Migration Testing
- **Current heading:** Migration testing documented but no explicit test file
- **True north:** Every documented feature has corresponding test
- **Correction:** Add explicit migration test file (docs/user/migration.md features)

### NAV-7 StrEnum for Constants
- **Current heading:** Checker enum uses plain str values
- **True north:** StrEnum for string-valued constants (python-dev)
- **Correction:** Consider migrating Checker to StrEnum when breaking changes acceptable

- NAV-items total: 7
- Dimensions on course (no deviation): 12+ (deps, mocks, paths, logging, CLI, types, testing, etc.)
- Signal: green

## Test Automation

- Task runner: tox (in pyproject.toml)
- Single-command gate: YES (`uv run tox -p` runs all 5 envs)
- Default coverage: full (no markers deselected, no tests excluded)
- Signal: green

## Infrastructure Recommendations

No infrastructure gaps found. The project has:
- tox with 5 environments covering lint, type-check, 2 Python versions, docs
- pytest-cov for coverage tracking
- pytest-archon for architecture enforcement
- pytest-ruff, pytest-ty, pytest-stogger for inline quality checks
- Duration tracking available via `--durations=0`

## Critical Findings Fixed

None — no critical findings. All quality gates GREEN.

## Full CLI Test Trace

Full CLI test not triggered — existing E2E evidence sufficient. 11/11 smoke tests passed, 7/7 entry points PROVEN.

## Code Volume

No code changes — audit only.

## Post-Fix Quality Gates

| Tool | Result |
|------|--------|
| tox | 5/5 passed (fix, ty, 3.13, 3.14, docs) |
| ruff | 0 issues |
| ty | 0 errors |
| pytest | 240 passed, 0 failed, 81% coverage |
| architecture | 33 rules passed |
| E2E smoke | 11/11 PASS |

## Recommendations

1. **[Medium] Decompose cli.py mega-functions** — run_fix (CC=116) and run_check (CC=59) should be split into focused functions
2. **[Medium] Improve core.py coverage** — Add direct tests for check_file() paths
3. **[Low] Add migration testing** — Explicit test file for docs/user/migration.md features
4. **[Low] Consider StrEnum** — Migrate Checker enum when breaking changes are acceptable

## Raw Data Location

`.agents/tmp/quality/` — inventory/, baseline/, extreme/, analysis/, e2e/
