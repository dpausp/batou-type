# Usage

## Choosing a Checker

`batou-type` supports two type checkers.
Use `-c` to select:

```{code-block} shell
$ batou-type check                      # ty (default)
$ batou-type check -c mypy              # mypy only
$ batou-type check -c ty -c mypy        # both, in sequence
```

Pass `-c` multiple times to run several checkers.
Each checker processes every component file independently.

### ty (default)

Fast, modern Python type checker.
No extra flags needed.

### mypy

Runs with flags tailored for batou components: `--explicit-package-bases`,
`--check-untyped-defs`, `--no-incremental`. You do not need to pass these — `batou-type`
adds them automatically.

### Passing extra flags to ty

Use `--ty-args` to forward additional arguments:

```{code-block} shell
$ batou-type check --ty-args "--output-format concise"
```

## JSON Output

Use `--json` (or `--output-format json`) for machine-readable output:

```{code-block} shell
$ batou-type check --json
$ batou-type check --output-format json
```

In JSON mode, structured results go to **stdout** and all progress messages (stub
loading, venv detection, project discovery) go to **stderr**. This keeps the JSON
payload clean for piping:

```{code-block} shell
$ batou-type check --json | jq .summary
```

Example JSON output (with errors):

```{code-block} json
{
  "schema_version": "1.0.0",
  "projects": [
    {
      "path": ".",
      "components": [
        {
          "path": "components/app/component.py",
          "diagnostics": [
            {
              "file": "components/app/component.py",
              "line": 15,
              "column": 10,
              "message": "Cannot access member \"misspelled_attribute\" on type \"Component\"",
              "code": "unresolved-attribute",
              "severity": "major",
              "checker": "ty"
            }
          ]
        }
      ]
    }
  ],
  "summary": {
    "total_projects": 1,
    "total_components": 1,
    "total_errors": 1
  },
  "metadata": {
    "checker": ["ty"]
  }
}
```

To print the JSON Schema that defines this format:

```{code-block} shell
$ batou-type check --show-schema
```

Exit codes are unchanged in JSON mode — see [](#exit-codes).

## How Projects Are Discovered

`batou-type` identifies a batou project by the presence of a `components/` directory:

```
my-deployment/
├── components/
│   ├── app/component.py
│   ├── database/component.py
│   └── webserver/component.py
├── environments/
└── ...
```

When you pass a directory that is not itself a batou project, the tool scans its
immediate subdirectories.
This lets you check multiple deployments at once:

```{code-block} shell
$ batou-type check /path/to/all-deployments/
```

If no projects with `components/` directories are found, the tool prints
`No batou projects found in {paths}` and exits cleanly (code 0).

## Virtual Environment Detection

`batou-type` automatically detects project-level virtual environments and adds their
site-packages to the type checker’s search path.
Supported:

- `.venv/` — standard venvs (e.g. created by uv)
- `appenv` — batou’s bundled environment manager

No configuration needed.
Detection happens silently unless `-v` is used.

## Verbose Output

Use `-v` to see internal details — resolved PYTHONPATH, discovered site-packages, stub
loading:

```{code-block} shell
$ batou-type check -v
```

Useful for troubleshooting when type errors reference modules that should be available.

## Version Information

```{code-block} shell
$ batou-type version
```

Shows the tool version and status of loaded stub packages:

```{code-block} text
batou-type 1.2.3
  batou-stubs 0.5.0 @ /path/to/batou
  batou_ext-stubs vendored @ /path/to/vendor/batou_ext
```

Stubs marked `<not installed>` means no external stub package was found and no vendored
fallback exists.

## Exit Codes

| Code | Meaning |
| --- | --- |
| 0 | No type errors, or no component files found. In `--diff` mode: no diffs present |
| 1 | At least one component has type errors. In `--diff` mode: diffs present |
| 2 | Type checker not available (e.g. ty not installed) |

Use exit codes in CI pipelines to fail builds on type errors:

```{code-block} shell
$ batou-type check || exit 1
```

## Autofix

`batou-type` can automatically fix two recurring classes of type-check diagnostics:

**Missing submodule imports** (`possibly-missing-submodule`) : Inserts
`from batou_ext.X import Y` for accessed but unimported modules.

**`self._` dereferencing** (`unresolved-attribute`) : Transforms `self += X` to
`self += (_ := X)` where `self._` is referenced in the same scope, then replaces
`self._` with `_`.

### Fix Flags

| Flag | Effect |
| --- | --- |
| `--fix` | Apply fixes in-place, write modified files |
| `--diff` | Print unified diff, do not write files. Implies `--fix-only` |
| `--fix-only` | Apply fixes, suppress per-component error report. Implies `--fix` |
| `--virtual` | Verify fixes in a temporary directory before writing. Composes with other fix flags |

### Flag Implication Chain

```
--diff       →  --fix-only  →  --fix
```

`--diff` implies `--fix-only` (no error report, diff only).
`--fix-only` implies `--fix` (fixes are computed).
You never need to pass `--fix --fix-only` — the implication chain handles it.

### Examples

```{code-block} shell
$ batou-type check --fix            # Fix in-place
$ batou-type check --diff            # Preview fixes as unified diff
$ batou-type check --fix --virtual   # Fix with tempdir safety check
$ batou-type check --diff --virtual  # Diff with tempdir safety check
$ batou-type check --fix-only        # Fix, hide per-component error report
$ batou-type check --fix -v          # Fix with verbose output
$ batou-type check --diff -c ty      # Diff for ty checker only
```

### Diff Output Format

`--diff` produces unified diff output with `a/` and `b/` file prefixes, rendered with
syntax highlighting:

```diff
--- a/components/app/component.py
+++ b/components/app/component.py
@@ -1,3 +1,4 @@
+from batou_ext.ssl import SSL
 class App(Component):
     def configure(self):
         self += SSL(hostname=self.hostname)
```

After the diff, a summary line appears:

```{code-block} text
1 fixable file(s) (run without --diff to apply)
```

When diffs exist, exit code is 1. When no diffs exist, exit code is 0.

### Virtual Mode

`--virtual` copies component files into a temporary directory, applies fixes there, and
runs a full type-check on the copies.
If the fix does not reduce the total error count, it prints:

```{code-block} text
Fix did not reduce errors, skipping
```

The fix is discarded and the command exits with code 1. This catches cases where an
autofix transformation is syntactically valid but introduces new type errors.

Use `--virtual` in CI pipelines for safety.

## pytest Integration

Add type checking to your pytest test suite with `--batou-ty`:

```{code-block} shell
$ pytest --batou-ty
```

This activates a plugin that:

1. Collects all `components/**/*.py` files as test items
2. Runs ty on each component before the test session
3. Reports type errors as test failures

Each component file appears as a single test item marked with the `batou_ty` marker.
A failing type check produces a diagnostic message:

```{code-block} text
FAILED components/app/component.py::batou_ty - Type check failed with 3 error(s)
```

Filter with pytest’s standard options:

```{code-block} shell
$ pytest --batou-ty -m batou_ty       # run only type-check tests
$ pytest --batou-ty -k "app"          # type-check only matching components
```

## Migration Testing

Use `batou-type` to preview breaking changes before upgrading batou in production:

1. Install a **newer** version of `batou-type` (which ships updated stubs) alongside
   your existing deployment.
2. Run `batou-type check`.
3. Type errors reveal API changes, removed attributes, or signature shifts that would
   break on upgrade.

Fix the reported issues in your components, then upgrade batou with confidence.

## What batou-type Does Not Do

- It does **not** run your deployment or execute any component code.
- It does **not** install or manage batou itself.
- It checks only `components/**/*.py` files — other Python files in your deployment are
  ignored.
- Stub coverage may not include every batou API. If you encounter false positives, check
  whether the relevant stubs exist in the vendored or installed stub packages.
