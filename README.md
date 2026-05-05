# batou-typecheck

Type-check batou deployment components against batou stubs.

Finds all `components/**/*.py` files in the current directory and runs type checkers on them.

## Usage

```
batou-typecheck                          # ty (default)
batou-typecheck -c mypy                  # mypy only
batou-typecheck -c ty -c mypy            # both checkers
batou-typecheck --fix                    # fix in-place
batou-typecheck --diff                   # preview fixes as unified diff
batou-typecheck --fix --virtual          # fix with tempdir safety check
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

Pass `-c` multiple times to run several checkers in sequence. Each checker sees each component file individually.

## Autofix

Automatically fix two recurring type-check warning classes:

- **Missing submodule imports** — inserts `from batou_ext.X import Y` for unimported modules
- **`self._` dereferencing** — transforms `self += X` to `self += (_ := X)` (walrus) where needed

```
batou-typecheck --fix            # fix in-place
batou-typecheck --diff           # preview fixes (unified diff, no write)
batou-typecheck --fix-only       # fix, suppress remaining error report
batou-typecheck --fix --virtual  # fix with tempdir verification
```

`--diff` implies `--fix-only`, `--fix-only` implies `--fix`. Diff output is compatible with `git apply`.

## Migration Testing
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
