# CLI Fix Pipeline

## Context

The CLI needed an autofix pipeline that applies automated fixes to type-check diagnostics while preserving the read-only lint behavior of `run_check()` for normal invocations. The pipeline supports multiple output modes: in-place fixes, diff-only output, and safe verification in a temporary directory.

## Decisions

### fix-pipeline

#### Context

`run_check()` handles linting and reporting. Mixing fix logic into it would complicate the read-only path and make it harder to reason about side effects. The fix pipeline has fundamentally different behavior: it modifies files and re-runs type checking.

#### Decision

`run_fix()` is a separate function from `run_check()`. Pipeline: (1) `check_all(json_mode=True)` → diagnostics, (2) group diagnostics by file, (3) apply matching fixers, (4) write/diff/verify based on flags. The read-only lint path (`run_check`) remains unchanged.

#### Alternatives

a. Integrate fix logic into `run_check()` with a conditional branch — rejected because it entangles two distinct responsibilities (reporting vs. modifying) in one function, making both paths harder to test and maintain.
b. A separate CLI subcommand `batou-type fix` — rejected because fix is an extension of the check workflow, not a different operation; the user expects `--fix` to be a flag on `check`, not a separate command.

#### Consequences

`run_fix()` has its own function signature and exit code semantics. It calls `check_all()` with `json_mode=True` internally to get structured diagnostics, independent of the user's `--json` flag. Both functions share project discovery and stub detection logic but diverge after that point.

### flag-dispatch

#### Context

The four fix-related flags (`--fix`, `--diff`, `--fix-only`, `--virtual`) have logical implications: showing diffs implies fixing only (suppress the normal error report), and fix-only implies fixing (you can't suppress a report you haven't generated). Users should not need to specify redundant flags.

#### Decision

CLI flag implication chain: `--diff` implies `--fix-only`, `--fix-only` implies `--fix`. When `fix` is true, dispatch to `run_fix()`. Implemented as a three-line cascade in `cli.py`.

#### Alternatives

a. Require users to specify all flags explicitly (e.g., `--fix --diff`) — rejected because it creates a poor UX where users must understand implementation coupling between flags.
b. Mutually exclusive flag groups — rejected because the flags are not mutually exclusive; they layer on top of each other. `--fix --diff` is valid and means "fix and show diff".

#### Consequences

Users can pass `--diff` alone and get the full behavior (fix + diff + no error report). The implication chain is linear and predictable: each flag adds behavior without removing any. When `fix` is true after resolving implications, the CLI dispatches to `run_fix()` instead of `run_check()`.

### virtual-mode-impl

#### Context

Applying automated fixes to a real project carries risk: a fix could introduce new type errors or break existing code. A dry-run verification step gives confidence before modifying the real project.

#### Decision

When `--virtual` flag is set, copy the project to a tempdir (including components, `pyproject.toml`, `.appenv`, `.venv`), apply fixes there, re-run `check_all()` to verify errors decreased. If `new_errors >= old_errors`, print warning and exit 1 without applying fixes to the real project.

#### Alternatives

a. Apply fixes directly and re-run verification on the real project — rejected because if the fix makes things worse, the user's files are already modified; rollback is unreliable.
b. Use git to create a temporary branch and revert on failure — rejected because it assumes git, creates side effects in the repository, and adds git as a runtime dependency.

#### Consequences

Virtual mode is safe by default: the real project is never modified unless verification passes. The copy includes project infrastructure (`.appenv`, `.venv`) so the type checker can resolve dependencies. The error count comparison is a simple heuristic — it does not verify that specific errors were fixed, only that the total count decreased.

### diff-generation

#### Context

Users need to review proposed fixes before applying them. A unified diff output is the standard way to show changes and is pipeable to tools like `patch` or `delta`.

#### Decision

When `--diff` flag is set, generate unified diff output using `difflib.unified_diff()` with `a/`/`b/` prefixed paths. Write to `sys.stdout`. Files are NOT modified in-place.

#### Alternatives

a. Use `subprocess.run(["diff", ...])` — rejected because it requires an external tool, fails on systems without GNU diff, and offers no advantage over the stdlib `difflib`.
b. Write patches to files — rejected because stdout output is pipeable and does not create cleanup burden.

#### Consequences

Diff mode is read-only: source files remain untouched. The exit code is 1 if any diffs exist (analogous to `git diff --exit-code`), 0 if nothing to fix. The `a/`/`b/` prefix convention matches `git diff` output, making it familiar to users and compatible with diff-viewing tools.

## Verified By

- `tests/test_fixer_integration.py::TestRunFixNoFixable::test_clean_project_no_fixable_diagnostics` — verifies clean project exits 0
- `tests/test_fixer_integration.py::TestRunFixSelfDeref::test_diff_mode_produces_unified_diff` — verifies diff mode is read-only
- `tests/test_fixer_integration.py::TestRunFixSelfDeref::test_fix_mode_writes_in_place` — verifies in-place write
- `tests/test_fixer_integration.py::TestRunFixFlags::test_fix_only_suppresses_errors_exits_zero` — verifies fix-only flag semantics
- `tests/impl_spec/test_autofix_missing_imports.py::TestCLIFlags` — verifies all four CLI flags exist
- `tests/impl_spec/test_autofix_missing_imports.py::TestFlagImplications` — verifies flag implication chain
- `tests/impl_spec/test_autofix_missing_imports.py::TestRunFixFunction` — verifies `run_fix()` is importable with expected params
