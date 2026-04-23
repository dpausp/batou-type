# batou-typecheck

Type-check batou deployment components against batou stubs.

Finds all `components/**/*.py` files in the current directory and runs type checkers on them. No configuration needed — run it in your deployment root and it works.

## Installation

TODO: add pip/uv install instructions

## Usage

```
batou-typecheck                          # ty (default)
batou-typecheck -c mypy                  # mypy only
batou-typecheck -c basedpyright          # basedpyright only
batou-typecheck -c ty -c mypy -c basedpyright  # all three
```

### Output

Status messages go to stderr, checker output goes to stdout:

```
$ batou-typecheck
Type-checking 42 component file(s) ...
--- ty ---
components/app/component.py:15: error: ...
```

Exit code **0** — no errors (or no component files found). Exit code **1** — at least one type error detected.

## Checkers

| Checker | Notes |
|---|---|
| `ty` | Default. Fast, modern Python type checker. |
| `mypy` | Runs with `--explicit-package-bases --check-untyped-defs --no-incremental`. |
| `basedpyright` | Strict pyright fork. Known batou false positives (uninitialized variables, implicit overrides, unannotated class attributes) are filtered automatically. |

Pass `-c` multiple times to run several checkers in sequence. Each checker sees each component file individually.

## Migration Testing

Use `batou-typecheck` to preview breaking changes *before* upgrading batou in production:

1. Install a **newer** version of `batou-typecheck` (which ships updated stubs) in your **existing** deployment directory.
2. Run `batou-typecheck`.
3. Type errors reveal API changes, removed attributes, or signature shifts that would break on upgrade.

Fix the reported issues in your components, then upgrade batou itself with confidence.

## What It Checks

The tool discovers every `components/**/*.py` file relative to where you run it. This matches the standard batou deployment layout:

```
my-deployment/
├── components/
│   ├── app/component.py
│   ├── database/component.py
│   └── webserver/component.py
├── environments/
└── ...
```

If no component files are found, the tool prints a message to stderr and exits cleanly.
