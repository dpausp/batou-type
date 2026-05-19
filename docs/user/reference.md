# Reference

All flags, formats, and exit codes for `batou-type check`.

## Checker Selection

| Flag | Effect |
| --- | --- |
| `-c ty` | Run ty (default) |
| `-c mypy` | Run mypy with batou-specific flags |
| `-c ty -c mypy` | Run both checkers in sequence |

ty runs by default when you omit `-c`.

mypy receives `--explicit-package-bases`, `--check-untyped-defs`, and `--no-incremental` automatically.

### Extra ty flags

Pass additional arguments to ty with `--ty-args`:

```{code-block} shell
$ batou-type check --ty-args "--output-format concise"
```

Available formats: `concise`, `rich` (default). See `ty --help` for the full list.

## JSON Output

```{code-block} shell
$ batou-type check --json
$ batou-type check --output-format json
```

Structured results go to **stdout**, progress messages (stub loading, venv detection, project discovery) go to **stderr**. Pipe cleanly:

```{code-block} shell
$ batou-type check --json | jq .summary
```

### JSON structure (with errors)

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

### JSON structure (no errors)

```{code-block} json
{
  "schema_version": "1.0.0",
  "projects": [
    {
      "path": ".",
      "components": []
    }
  ],
  "summary": {
    "total_projects": 1,
    "total_components": 0,
    "total_errors": 0
  },
  "metadata": {
    "checker": ["ty"]
  }
}
```

### Print the JSON Schema

```{code-block} shell
$ batou-type check --show-schema
```

## Project Discovery

`batou-type` identifies a batou project by the presence of a `components/` directory.

When you pass a directory that is not itself a batou project, the tool scans its immediate subdirectories. This checks multiple deployments at once:

```{code-block} shell
$ batou-type check /path/to/all-deployments/
```

If no `components/` directories are found, the tool prints `No batou projects found in {paths}` and exits with code 0.

## Virtual Environment Detection

`batou-type` detects project-level virtual environments and adds their site-packages to the type checker's search path.

Supported layouts:

- `.venv/` — standard venvs (e.g. created by uv)
- `appenv` — batou's bundled environment manager

No configuration needed. Detection runs silently unless you pass `-v`.

## Verbose Output

```{code-block} shell
$ batou-type check -v
```

Shows resolved PYTHONPATH, discovered site-packages, and stub loading. Use this when type errors reference modules that should be available.

## Version

```{code-block} shell
$ batou-type version
```

Output:

```{code-block} text
2026-05-19T20:03:12Z I version                        batou-type 2.8.0
2026-05-19T20:03:12Z I stub-info                        batou-stubs vendored @ /path/to/vendor/batou
2026-05-19T20:03:12Z I stub-info                        batou_ext-stubs vendored @ /path/to/vendor/batou_ext
```

Stubs marked `<not installed>` means no external stub package was found and no vendored fallback exists. Timestamps vary per run.

## Exit Codes

| Code | Condition |
| --- | --- |
| 0 | No type errors, or no component files found. With `--diff`: no diffs present |
| 1 | At least one component has type errors. With `--diff`: diffs present |
| 2 | Type checker not available (e.g. ty not installed) |

Use in CI:

```{code-block} shell
$ batou-type check || exit 1
```

## Autofix Flags

| Flag | Effect |
| --- | --- |
| `--fix` | Apply fixes in-place, write modified files |
| `--diff` | Print unified diff without writing files. Implies `--fix-only` |
| `--fix-only` | Apply fixes, suppress per-component error report. Implies `--fix` |
| `--virtual` | Verify fixes in a temporary directory before writing. Composes with other fix flags |

Implication chain: `--diff` → `--fix-only` → `--fix`. Passing `--fix --fix-only` is redundant — the chain handles it.

## What batou-type Does Not Do

- Does not run your deployment or execute any component code.
- Does not install or manage batou itself.
- Checks only `components/**/*.py` files — other Python files in your deployment are ignored.
- Stub coverage may not cover every batou API. If you hit false positives, check whether the relevant stubs exist in the vendored or installed stub packages.
