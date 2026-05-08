# Usage

## Project Setup

Before type checking works in your IDE, run setup once in your batou deployment project:

```{code-block} shell
$ batou-type setup
```

This command:

1. Detects whether your project uses `batou_ext` (by scanning `components/`)
2. Installs `batou-stubs` and `ty` as dev dependencies via `uv add --dev`
3. Installs `batou_ext-stubs` automatically if `batou_ext` usage is detected
4. Writes a minimal `[tool.ty]` configuration to `pyproject.toml

After setup, `ty check components/` produces the same diagnostics as `batou-type check`. Your IDE (PyCharm, Neovim with ty LSP) picks up the stubs from the project venv automatically — zero manual configuration.

### Setup Options

| Flag | Effect |
|------|--------|
| `--checker ty` | Install and configure ty (default) |
| `--checker mypy` | Install and configure mypy instead |
| `--no-ext` | Skip `batou_ext-stubs` even if batou_ext usage is detected |
| `--stub-source PATH` | Use local stub packages instead of PyPI (for testing) |
| `-v` | Verbose output |

### Local Stub Testing

If `batou-stubs` is not yet on PyPI, test with a local path:

```{code-block} shell
$ batou-type setup --stub-source ../batou/stubs
```

This resolves `../batou/stubs/batou-stubs` and `../batou/stubs/batou_ext-stubs` as local packages.

### Requirements

- The project must have a `pyproject.toml` in the root directory
- [uv](https://docs.astral.sh/uv/) must be available

## Choosing a Checker

`batou-type` supports two type checkers. Use `-c` to select which one runs:

```{code-block} shell
$ batou-type check                      # ty (default)
$ batou-type check -c mypy              # mypy only
$ batou-type check -c ty -c mypy        # both, in sequence
```

Pass `-c` multiple times to run several checkers. Each checker processes every component file independently.

### ty (default)

Fast, modern Python type checker. Ships as the default — no extra flags needed.

### mypy

Runs with flags tailored for batou components: `--explicit-package-bases`, `--check-untyped-defs`, `--no-incremental`. You do not need to pass these yourself — `batou-type` adds them automatically.

### Passing extra flags to ty

Use `--ty-args` to forward additional arguments:

```{code-block} shell
$ batou-type check --ty-args "--output-format concise"
```

## JSON Output

Use `--json` (or `--output-format json`) to produce machine-readable JSON instead of human-readable output:

```{code-block} shell
$ batou-type check --json .
$ batou-type check --output-format json .
```

This is designed for piping into LLM tools, CI pipelines, or any downstream processing:

```{code-block} shell
$ batou-type check --json . | llm-tool
```

In JSON mode, the structured result goes to **stdout** while all diagnostic messages (progress, stub loading, venv detection) go to **stderr**. This keeps the JSON payload clean for piping.

To inspect the JSON Schema that defines the output format:

```{code-block} shell
$ batou-type check --show-schema
```

The schema is also available as a `$schema` property inside every JSON output.

Exit codes are unchanged in JSON mode — see [](#exit-codes) below.

## How Projects Are Discovered

`batou-type` identifies a batou project by the presence of a `components/` directory. This matches the standard batou deployment layout:

```
my-deployment/
├── components/
│   ├── app/component.py
│   ├── database/component.py
│   └── webserver/component.py
├── environments/
└── ...
```

When you pass a directory that is not itself a batou project, the tool scans its immediate subdirectories. This lets you check multiple deployments at once:

```{code-block} shell
$ batou-type check /path/to/all-deployments/
```

If no component files are found, the tool prints a message and exits cleanly (code 0).

## Virtual Environment Detection

`batou-type` automatically detects project-level virtual environments and adds their site-packages to the type checker's search path. It supports:

- `.venv/` — standard venvs (e.g., created by uv)
- `appenv` — batou's bundled environment manager

No configuration needed. If neither is found, the tool prints a warning but continues checking.

## Verbose Output

Use `-v` to see diagnostic details — resolved PYTHONPATH, discovered site-packages directories:

```{code-block} shell
$ batou-type check -v
```

This is useful for troubleshooting when type errors reference modules that should be available.

## Version Information

```{code-block} shell
$ batou-type version
```

Shows the tool version and the status of loaded stub packages (whether vendored or installed separately).

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | No type errors detected (or no component files found). In `--diff` mode: no diffs present |
| 1 | At least one component has type errors, or diffs present in `--diff` mode |
| 2 | Invalid command-line usage (wrong flag, unknown checker name) |

Use the exit code in CI pipelines to fail builds on type errors.

In JSON mode, all diagnostics (type errors, hints, code references) appear as structured `Diagnostic` objects inside the JSON output on stdout. Infrastructure messages remain on stderr.


## Autofix

`batou-type` can automatically fix two recurring classes of type-check warnings:

- **Missing submodule imports** (`possibly-missing-submodule`) — inserts `from batou_ext.X import Y` for accessed but unimported modules
- **`self._` dereferencing** — transforms `self += X` to `self += (_ := X)` (walrus) where `self._` is referenced, then replaces `self._` with `_` in the same scope

### Fix Flags

Four flags control fix behavior, following [ruff's](https://docs.astral.sh/ruff/linter/#fixing) convention:

| Flag | Effect |
|------|--------|
| `--fix` | Apply fixes in-place, write modified files |
| `--diff` | Print unified diff, do not write files. Implies `--fix-only` |
| `--fix-only` | Apply fixes, suppress remaining error report. Implies `--fix` |
| `--virtual` | Verify fixes in a tempdir before writing. Composes with `--fix`, `--diff`, `--fix-only` |

### Flag Implication Chain

```
--diff       →  --fix-only  →  --fix
```

`--diff` implies `--fix-only` (no error report, diff only). `--fix-only` implies `--fix` (fixes are applied). You never need to pass `--fix --fix-only` — the implication chain handles it.

### Examples

```{code-block} shell
$ batou-type check --fix            # Fix in-place
$ batou-type check --diff            # Preview fixes as unified diff
$ batou-type check --fix --virtual   # Fix with tempdir safety check
$ batou-type check --diff --virtual  # Diff with tempdir safety check
```

Fix flags compose with existing flags:

```{code-block} shell
$ batou-type check --fix -v          # Fix with verbose output
$ batou-type check --diff -c ty      # Diff for ty checker only
$ batou-type check --fix-only        # Fix, hide remaining errors
```

### Diff Output Format

`--diff` produces unified diff output compatible with `git apply`:

```{code-block} diff
--- a/components/app/component.py
+++ b/components/app/component.py
@@ -1,3 +1,4 @@
+from batou_ext.ssl import SSL
 class App(Component):
     def configure(self):
         self += SSL(hostname=self.hostname)
```

When diffs exist, exit code is 1. When no diffs exist, exit code is 0.

### Virtual Mode

`--virtual` copies component files into a temporary directory (using reflinks on CoW filesystems for efficiency), applies fixes there, and runs a full type-check on the copies. If the fix does not reduce the error count, the fix is skipped and a message is printed.

Use `--virtual` in CI pipelines for safety — it catches cases where an autofix transformation is syntactically valid but introduces new type errors.

## pytest Integration

If you write tests for your batou deployment, you can integrate type checking into your pytest suite using the `--batou-ty` flag:

```{code-block} shell
$ pytest --batou-ty
```

This activates a pytest plugin that:

1. Collects all `components/**/*.py` files as test items
2. Runs ty on each component before the test session
3. Reports type errors as test failures with diagnostic output

Each component file appears as a single test item marked with `batou_ty`. A failing type check produces a clear error count:

```{code-block} text
FAILED components/app/component.py::batou_ty - Type check failed with 3 error(s)
```

Combine with pytest's standard filtering to control execution:

```{code-block} shell
$ pytest --batou-ty -m batou_ty       # run only type-check tests
$ pytest --batou-ty -k "app"          # type-check only matching components
```

## Migration Testing

Use `batou-type` to preview breaking changes *before* upgrading batou in production:

1. Install a **newer** version of `batou-type` (which ships updated stubs) in your **existing** deployment directory.
2. Run `batou-type check`.
3. Type errors reveal API changes, removed attributes, or signature shifts that would break on upgrade.

Fix the reported issues in your components, then upgrade batou itself with confidence.

## What batou-type Does Not Do

- It does **not** run your deployment or execute any component code.
- It does **not** install or manage batou itself.
- It checks only `components/**/*.py` files — other Python files in your deployment are ignored.
- Stub coverage may not include every batou API. If you encounter false positives, check whether the relevant stubs exist.
