# batou-type

Type-check batou deployment components against batou stubs.

Finds all `components/**/*.py` files in the current directory and runs type checkers on them.

## Usage

```
batou-type check                      # ty (default)
batou-type check -c mypy              # mypy only
batou-type check -c ty -c mypy        # both checkers
batou-type check --fix                # fix in-place
batou-type check --diff               # preview fixes as unified diff
batou-type check --fix --virtual      # fix with tempdir safety check
```
### Output

Status messages go to stderr, checker output goes to stdout:

```
$ batou-type check
Scanning /path/to/deployment ...
Type-checking 42 component file(s) ...
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
batou-type check --fix            # fix in-place
batou-type check --diff           # preview fixes (unified diff, no write)
batou-type check --fix-only       # fix, suppress remaining error report
batou-type check --fix --virtual  # fix with tempdir verification
```

`--diff` implies `--fix-only`, `--fix-only` implies `--fix`. Diff output is compatible with `git apply`.

## Migration Testing

Use `batou-type` to preview breaking changes *before* upgrading batou in production:

1. Install a **newer** version of `batou-type` (which ships updated stubs) in your **existing** deployment directory.
2. Run `batou-type check`.
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
