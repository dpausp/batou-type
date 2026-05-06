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

Exit code **0** — no errors (or no component files found). Exit code **1** — at least one type error detected.

## Autofix

Automatically fix missing `batou_ext.*` imports and `self._` dereferencing. See [usage docs](docs/user/usage.md#autofix) for flags and examples.

## Migration Testing

Install a newer `batou-type` in an existing deployment — type errors reveal API changes before upgrading batou. See [usage docs](docs/user/usage.md#migration-testing).

## What It Checks

Discovers every `components/**/*.py` file and runs type checkers on them. Virtual environments (`.venv/`, `appenv`) are added to the search path automatically. If no component files are found, exits cleanly.

Full documentation: [docs/user/usage.md](docs/user/usage.md)
