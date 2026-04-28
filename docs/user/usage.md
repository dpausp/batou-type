# Usage

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
| 0 | No type errors detected (or no component files found) |
| 1 | At least one component has type errors |
| 2 | Invalid command-line usage (wrong flag, unknown checker name) |

Use the exit code in CI pipelines to fail builds on type errors.

In JSON mode, all diagnostics (type errors, hints, code references) appear as structured `Diagnostic` objects inside the JSON output on stdout. Infrastructure messages remain on stderr.

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
