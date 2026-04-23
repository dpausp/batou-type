# Stream D: E2E Coverage + Production Reality

## Verdict: ORANGE (with significant gaps)

## Entry Point E2E Status

### CLI Subcommands

#### `version` — PROVEN

E2E evidence from `.agents/tmp/quality/e2e/version.txt`:
```
batou-type 2.8.0.dev0
  batou-stubs <not installed>
  batou_ext-stubs <not installed>
```

The command executes, produces correct output format, handles missing stubs gracefully. **No automated test** — this was manually captured.

#### `check` (no components) — PROVEN (partial)

E2E evidence from `.agents/tmp/quality/e2e/check-no-args.txt`:
```
Loaded stubs
batou-stubs <not installed>
batou_ext-stubs <not installed>

No component files found in components/
```

Correctly shows stub table, correctly reports no components, correctly exits with code 0 (implied by capture, not explicitly verified).

**NOT PROVEN:**
- `check` with actual component files present
- `check` with type errors in components
- `check` with `-c mypy` or `-c basedpyright` flags
- Exit code 1 when errors found
- Error output formatting with real type-checker output
- `check` with multiple `-c` flags simultaneously

#### `check --help` — PROVEN

E2E evidence confirms correct help output with checker options.

#### Bad command — PROVEN

E2E evidence confirms error message for nonexistent command.

#### Bare invocation — PROVEN

E2E evidence confirms help is shown when no subcommand given.

### Pytest Plugin — UNKNOWN

**Zero E2E evidence.** The plugin:
- Registers `--batou-ty` CLI flag
- Registers `batou_ty` marker
- Collects `components/**/*.py` files as test items
- Runs `check_all()` upfront and stashes results
- Each component file becomes a test item that fails if type errors exist

No test exercises this flow. No test invokes `pytest --batou-ty` against a real project with components. The plugin could:
- Fail to collect component files
- Crash during `check_all()` invocation
- Produce wrong test item names
- Fail to report errors correctly

### Public API (Library) — UNKNOWN

| Function | E2E Status | Notes |
|---|---|---|
| `Checker` enum | PROVEN | Import smoke test + `Checker.ty.value == "ty"` assertion |
| `TypeCheckResult` | SUSPECTED | Import works, never instantiated in tests |
| `check_all()` | UNKNOWN | Never called in tests; invokes subprocess |
| `check_file()` | UNKNOWN | Never called in tests; the core execution path |
| `find_components()` | UNKNOWN | Never called with real filesystem in tests |
| `__version__` | PROVEN | Import test + E2E version output confirms |

### Documented Features Coverage

| Feature | Tested? | E2E Evidence |
|---|---|---|
| Default checker is ty | Partial | Contract test checks enum value, not runtime behavior |
| Multiple checkers via `-c` | NO | No test, no E2E capture |
| Component discovery glob | NO | No test with real components/ directory |
| Exit code 0/1 | NO | No test, E2E only captured output (not exit codes) |
| Exit code 0 when no components | NO | E2E captured output but not exit code explicitly |
| basedpyright noise filtering | NO | `_filter_basedpyright_json` never tested |
| mypy flags | NO | Never exercised |
| Status to stderr, output to stdout | NO | Never verified |
| `python -m batou_type` | Partial | E2e tests used `python -m batou_type`, so it works |
| `--batou-ty` pytest flag | NO | Never exercised |
| `batou_ty` marker | NO | Never exercised |
| Version shows stub info | PROVEN | E2E capture confirms |
| Stubs table before checking | PROVEN | E2E capture confirms |

## Production Reality Assessment

### What Actually Works (E2E proven)

1. `batou-type version` — produces correct output
2. `batou-type check` with no components — shows stub table, reports no components
3. `batou-type --help` / `batou-type check --help` — correct help text
4. Error handling for bad commands — correct error message
5. Module structure — imports resolve correctly

### What Has Zero Proof of Working

1. **The core value proposition** — type-checking batou components — has NO test. `check_file()` and `check_all()` invoke `subprocess.run()` against real type checkers. This has never been tested.
2. **basedpyright JSON filtering** — `_filter_basedpyright_json()` parses JSON and filters diagnostics. Zero test coverage.
3. **Exit code semantics** — The README documents exit 0/1. The code uses `raise typer.Exit(0)` and `raise typer.Exit(1)`. Never verified.
4. **Multi-checker mode** — `check_file()` loops over checkers. The branching logic for ty vs mypy vs basedpyright is untested.
5. **Pytest plugin collection** — The `pytest_collect_file` hook filters for `components/**/*.py`. The `BatouComponentItem.runtest()` reads from stash and calls `pytest.fail()`. None of this is tested.

### What Could Break Silently

1. **Subprocess execution** — `check_file()` constructs commands from `CHECKER_COMMANDS` dict. If a checker is not installed, `subprocess.run()` will raise `FileNotFoundError`. The code does not handle this.
2. **basedpyright JSON parsing** — `_filter_basedpyright_json()` assumes `generalDiagnostics` key exists. If basedpyright changes its output format, this silently returns the raw output.
3. **Plugin stash key collision** — The plugin uses `pytest.StashKey` for result caching. If `pytest_collection_modifyitems` runs before files are collected (timing issue), results dict could be incomplete.
4. **`get_stub_versions()` exception handling** — Catches `except Exception` and returns `StubInfo(version=None)`. If `importlib.metadata.version()` raises something unexpected, it's silently swallowed.
