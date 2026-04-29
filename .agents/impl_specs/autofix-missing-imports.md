---
lifecycle: design
completed_at: 2026-04-29T16:08:44Z
git_rev: 6c03d16
---

# autofix-missing-imports

## Context

batou-type produces two recurring classes of type-check warnings that are mechanically fixable: missing submodule imports (`possibly-missing-submodule` for `batou_ext.*` access without prior import) and `self._` dereferencing (accessing the last sub-component through the `Component | None` typed `self._` attribute instead of a concrete type). Both patterns appear frequently across deployments. Manual fixing is tedious. This spec adds automated fix capabilities following ruff's `--fix`/`--diff`/`--fix-only` UX model.

## Decisions

### module-placement

#### Context

The existing four-layer architecture (`vendor/ → core.py → output.py → cli.py`) is enforced by pytest-archon. `core.py` is stdlib-only. Fixer code requires libcst for AST transformation, which is a non-stdlib dependency. The fixer also needs the `Diagnostic` model from `output.py`.

#### Decision

New module `src/batou_type/fixer.py`. Dependency graph extension: `cli.py → fixer.py → output.py → core.py`. `fixer.py` imports from `output.py` (Diagnostic model) and libcst. Called from `cli.py` only. No changes to `core.py`, `output.py`, or existing architecture rules for those modules.

#### Alternatives

a. Fixer code in `cli.py` — monolithic, already 320 lines
b. `src/batou_type/fixers/` package — over-engineering for exactly two fixers
c. Fixer in `core.py` with lazy libcst import — breaks stdlib-only constraint

#### Consequences

New dependency branch in the import graph. pytest-archon rules must be extended to cover `fixer.py` layer constraints.

### fixer-protocol

#### Context

Two fixers need a uniform interface so the pipeline can discover, filter, and dispatch diagnostics to the right fixer without hardcoded conditionals.

#### Decision

Dataclass-based protocol. Each fixer is a `Fixer` dataclass with `slug: str`, `diagnostic_codes: frozenset[str]` (claim criterion), and function signature `apply(source: str, diagnostics: list[Diagnostic]) -> str | None`. Returns `None` if nothing changed. No ABC, no Protocol class — two instances, done.

#### Alternatives

a. Free functions per fixer — no common interface, blocks future `--fixable` filter
b. Plugin registry with entry-points — extensibility explicitly not needed
c. ABC with abstract methods — formality overhead for two implementations

#### Consequences

Simple, testable. `slug` field enables future `--fixable` filtering without structural changes.

### diagnostic-matching

#### Context

The pipeline must route each diagnostic to the correct fixer based on the diagnostic's error code.

#### Decision

Fixer declares `diagnostic_codes: frozenset[str]`. Pipeline filters `result.errors` by code, groups by file, passes only matched diagnostics to the claiming fixer. One code maps to exactly one fixer — no overlaps.

#### Alternatives

a. Fixer receives all diagnostics and self-filters — defensive overhead in every fixer
b. Regex on `message` text — fragile, ty message format not guaranteed stable
c. Multiple codes per fixer — unnecessary complexity, current mapping is 1:1

#### Consequences

Deterministic routing. Adding a new fixer requires only declaring its codes.

### add-missing-import-impl

#### Context

The `possibly-missing-submodule` diagnostic identifies a module path (e.g. `batou_ext.ssl`) that is accessed but not imported. The fixer must insert the correct import statement.

#### Decision

Extract module path from diagnostic message. libcst parses the AST, checks for existing imports of that module. If module already imported → merge new name into existing `from X import ...` statement. If not → insert new `from`-import at file top (after existing imports, before first non-import statement). Class/function name extracted from the offending line via libcst AST analysis.

#### Alternatives

a. Only bare `import batou_ext.ssl` — not batou convention, loses direct name access
b. Both names from diagnostic message via regex — ty message format not guaranteed stable
c. Skip if module already partially imported — leaves errors on the table

#### Consequences

Handles partial imports correctly (merging). libcst preserves formatting and comments.

### self-deref-impl

#### Context

`self._` is typed as `Component | None` in the stubs, so ty cannot resolve attribute access on it. The walrus operator `self += (_ := X)` gives `_` a concrete type.

#### Decision

Two-pass libcst transformation: (1) scan for all `self._` attribute accesses in the file. (2) For each `self += X` statement, check if any `self._` reference exists between it and the next `self +=` (or end of function). Only if `self._` is referenced → transform `self += X` to `self += (_ := X)` and replace all `self._` references in that scope with `_`. Scope is sequential statement order within the same function — no control-flow analysis. Chained access `self._.address` becomes `_.address`.

#### Alternatives

a. Transform all `self +=` unconditionally — unnecessary diff noise on unused assignments
b. Regex-based replacement — breaks on multi-line statements, string literals, comments
c. Only walrus, no `self._` → `_` replacement — user must manually change access sites

#### Consequences

Minimal diffs — only walruses where `_` is actually referenced. libcst handles all edge cases (multi-line, nested expressions).

### fix-pipeline

#### Context

The existing `run_check()` in `cli.py` handles lint-only mode. Fix mode needs a different flow: run ty with JSON output, parse diagnostics, apply fixers, write back or show diff.

#### Decision

Separate `run_fix()` function in `cli.py`. Flow: (1) reuse `check_all(json_mode=True)` to get diagnostics, (2) group diagnostics by file, (3) for each file with fixable diagnostics: read source, run matching fixers, collect transformed sources, (4) depending on flags: write in-place (`--fix`), output diff (`--diff`), or verify in tempdir (`--virtual`). `run_check()` remains unchanged.

#### Alternatives

a. Extend `run_check()` with fix logic — couples read-only and mutation paths
b. Fix in `core.py` — breaks stdlib-only constraint
c. Post-processing hook after `run_check()` — awkward separation of concerns

#### Consequences

Clean separation. `run_check()` untouched, zero regression risk. `run_fix()` shares project discovery and stub detection via the same helper functions.

### flag-dispatch

#### Context

Four new CLI flags (`--fix`, `--diff`, `--fix-only`, `--virtual`) must integrate with the existing `check` command following ruff's semantics.

#### Decision

Boolean Typer options on the existing `check` command. Implication chain: `--diff` implies `--fix-only`, `--fix-only` implies `--fix`. Dispatch: if any fix flag is set → call `run_fix()` instead of `run_check()`. No exclusive mode — fix flags compose with existing `--verbose` and `--checker` flags.

#### Alternatives

a. Separate `batou-type fix` subcommand — breaks ruff-UX convention from requirements
b. `--fix` as exclusive mode blocking other flags — unnecessarily restrictive
c. `--fix` always calls both `run_check` and `run_fix` — double ty invocations

#### Consequences

Familiar ruff-style UX. Flag implication chain matches user expectations.

### diff-generation

#### Context

`--diff` must produce unified diff output compatible with `git apply` and standard Unix tooling.

#### Decision

`difflib.unified_diff` from stdlib. Headers: `--- a/{path}` / `+++ b/{path}`. Output per file, then summary line: `N fixable in M files (run without --diff to apply)`. Exit 0 if no diffs, exit 1 if diffs present (ruff semantics).

#### Alternatives

a. `git diff` subprocess on temp files — adds git as runtime dependency
b. Custom diff formatting — reinventing the wheel
c. Rich side-by-side — not pipeable, breaks git-apply compatibility

#### Consequences

Standard Unix tooling compatibility. No external dependencies for diff generation.

### virtual-mode-impl

#### Context

`--virtual` verifies fixes don't introduce new type errors by running ty on fixed copies before touching real files.

#### Decision

Create tempdir, copy component files + `pyproject.toml` + `.appenv` + `.venv` (with reflink where supported, fallback to regular copy). Apply fixers on copies. Run `check_all()` on tempdir with same search paths. Compare error count: fewer errors → proceed with diff/write; same or more → report "fix did not reduce errors, skipping". Cleanup via `tempfile.TemporaryDirectory`.

#### Alternatives

a. Copy entire project — wasteful for large deployments
b. Fix + verify on originals, `git checkout` on failure — needs git, risky
c. Virtual as default for `--fix` — too slow for interactive use

#### Consequences

Safety net for CI. Reflinks minimize cost on CoW filesystems (btrfs, XFS, APFS). Fallback ensures portability.

### fix-only-semantics

#### Context

`--fix-only` semantics must match ruff: apply fixes, suppress remaining violation reporting, don't exit non-zero for leftover violations.

#### Decision

`--fix-only` suppresses the human-readable error report (ANSI-formatted ty output per component) and the FAILED-COMPONENTS summary. Shows only: diff (if `--diff`), "Fixed N file(s)" confirmation. Exit 0 if fixes applied successfully, exit 1 only if fixer itself fails. Remaining ty errors are completely silenced.

#### Alternatives

a. Show remaining errors as short list — half measure, not ruff semantics
b. Suppress only exit code, keep output — reduces utility
c. No effect without `--diff` — contradicts ruff model

#### Consequences

Matches ruff exactly. Clean output for CI pipelines that only care about fix success.

### test-strategy

#### Context

The project has 79 tests with 0% mock ratio, enforced by convention. New fixer code needs the same discipline.

#### Decision

Three-tier testing: (1) Unit tests in `tests/test_fixer.py` — fixer functions receive source string + diagnostics, assert on transformed source string comparison. No subprocess, no ty invocation. (2) Integration tests in `tests/test_fixer_integration.py` — `run_fix()` on `tmp_path` projects with real component files. (3) E2E tests in existing `tests/test_functional.py` — subprocess `batou-type check --fix --diff` on test projects, assert on exit code and stdout.

#### Alternatives

a. E2E only — slow, doesn't isolate fixer logic
b. Unit tests with mock diagnostics — doesn't verify real ty diagnostic codes
c. Snapshot testing — high maintenance for evolving output

#### Consequences

Follows existing pyramid pattern. Unit tests are fast and deterministic. E2E tests validate the full pipeline.

### test-file-locations

#### Context

Project convention is separate test files per concern (test_core.py, test_functional.py, test_architecture.py).

#### Decision

`tests/test_fixer.py` for unit tests (fixer transformations). `tests/test_fixer_integration.py` for `run_fix()` integration on `tmp_path` projects. E2E fix tests added to existing `tests/test_functional.py`.

#### Alternatives

a. All in `tests/test_fixer.py` — single file grows large
b. `tests/fixers/` directory — over-engineering for two fixers
c. Docstring tests — violates project convention of separate test files

#### Consequences

Consistent with existing structure. Clear separation of test tiers.

### architecture-test-impact

#### Context

pytest-archon enforces the four-layer model at test time. A new module requires new rules.

#### Decision

Add rules to `tests/test_architecture.py`: `fixer.py` may import from `output.py` (Diagnostic) and libcst, must not import from `cli.py`, `pytest_plugin.py`, or frameworks (typer, rich, pytest, structlog, stogger). `cli.py` may import from `fixer.py`. `fixer.py` must not import from `core.py` directly (goes through `output.py`).

#### Alternatives

a. No new rules — relies on existing catch-all rules, may miss violations
b. Treat `fixer.py` as CLI layer — allows framework imports that aren't needed
c. Treat `fixer.py` as output layer — wrong dependency direction

#### Consequences

Formal enforcement of the new module's layer position. Prevents accidental framework leakage into fixer code.

## Requirements

### Interface Contract

```
batou-type check                  # Lint-only (read-only, unchanged)
batou-type check --fix            # Fix in-place
batou-type check --diff           # Unified diff, no write (implies --fix-only)
batou-type check --fix-only       # Fix, suppress remaining error report (implies --fix)
batou-type check --fix --virtual  # Tempdir verification + fix
batou-type check --diff --virtual # Tempdir verification + diff
```

Discovery: `batou-type check --help` shows `--fix`, `--diff`, `--fix-only`, `--virtual` flags.

### Exit Codes

- 0: clean (no diagnostics) or no diffs (in `--diff` mode)
- 1: remaining issues or diffs present

### Scope

- INCLUDE: Two fixers (`add-missing-import`, `self-deref`), four CLI flags, libcst dependency, three-tier tests
- EXCLUDE: `--fixable` filter, `--unsafe-fixes` concept, additional fixers

## References

- docs/dev/architecture.md — four-layer model, framework isolation
- docs/dev/testing.md — test pyramid, 0% mock ratio convention
- Draft: `.agents/drafts/autofix-missing-imports.md` (source of binding decisions)
