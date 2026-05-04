# batou-type

Type-check batou deployment components against batou stubs.

Finds all `components/**/*.py` files and runs type checkers on them.

## Quick Start

```
$ pip install batou-type
$ batou-type check                  # type-check with ty (default)
```

Output example:

```
$ batou-type check
Found 1 project(s):
  /path/to/my-deployment

Checking 3 component(s) in my-deployment
app: passed
database: passed
webserver: passed
All 3 component(s) passed
```

Exit code **0** — no errors (or no component files found). Exit code **1** — at least one type error detected.

## Commands

| Command | Description |
|---------|-------------|
| `batou-type check [PATH…]` | Type-check component files (default command) |
| `batou-type version` | Show version and stub package status |

`batou-type` can also be invoked as `python -m batou_type`.

## Global Flags

| Flag | Description |
|------|-------------|
| `-v`, `--verbose` | Show diagnostic details (PYTHONPATH, site-packages) |
| `--json` | Machine-readable JSON output (aliases: `--output-format json`) |
| `--show-schema` | Print the JSON Schema for the JSON output format |

## Choosing a Checker

```
batou-type check                      # ty (default)
batou-type check -c mypy              # mypy only
batou-type check -c ty -c mypy        # both, in sequence
```

| Checker | Notes |
|---------|-------|
| `ty` | Default. Fast, modern Python type checker. |
| `mypy` | Runs with `--explicit-package-bases --check-untyped-defs --no-incremental`. |

Pass `-c` multiple times to run several checkers. Each processes every component file independently.

Pass extra flags to ty with `--ty-args`:

```
batou-type check --ty-args "--output-format concise"
```

## Autofix Mode

Automatically fix two recurring warning classes: missing `batou_ext.*` imports and `self._` dereferencing issues. Both use libcst for AST-preserving transformations.

| Flag | Behavior |
|------|----------|
| `--fix` | Fix in-place, write transformed files to disk |
| `--fix-only` | Fix in-place, suppress remaining error report (implies `--fix`) |
| `--diff` | Print unified diff instead of writing (implies `--fix-only`) |
| `--virtual` | Verify fixes in a tempdir before writing (use with `--fix` or `--diff`) |

Implication chain: `--diff` → `--fix-only` → `--fix`.

```
batou-type check --fix            # apply fixes in-place
batou-type check --diff           # preview fixes as unified diff
batou-type check --fix-only       # fix and suppress remaining errors
batou-type check --fix --virtual  # verify fixes in tempdir before writing
```

## pytest Integration

```shell
$ pytest --batou-ty                # type-check all components as test items
$ pytest --batou-ty -m batou_ty    # run only type-check tests
$ pytest --batou-ty -k "app"       # type-check only matching components
```

Requires the `pytest` optional dependency (`pip install batou-type[pytest]`).

## Project Discovery

`batou-type` identifies batou projects by a `components/` directory:

```
my-deployment/
├── components/
│   ├── app/component.py
│   ├── database/component.py
│   └── webserver/component.py
├── environments/
└── ...
```

When a directory is not itself a batou project, subdirectories are scanned. Pass a parent directory to check multiple deployments at once.

Virtual environments (`.venv/`, `appenv`) are detected automatically — their site-packages are added to the type checker's search path.

## Migration Testing

1. Install a **newer** version of `batou-type` (with updated stubs) in your existing deployment.
2. Run `batou-type check`.
3. Type errors reveal API changes that would break on upgrade.

Fix the reported issues, then upgrade batou with confidence.

## What batou-type Does Not Do

- Does **not** run your deployment or execute any component code.
- Does **not** install or manage batou itself.
- Checks only `components/**/*.py` files — other Python files are ignored.
- Stub coverage may not include every batou API.

---

Full documentation: [docs/user/usage.md](docs/user/usage.md)
