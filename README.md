# batou-type

Type-check batou deployment components against bundled stubs — catches attribute errors and missing imports before deploying.

## Install

```
uv add --dev batou-type
```

or

```
pip install batou-type
```

## Quick start

```
batou-type setup                      # configure project (run once)
batou-type check                      # type-check all components
batou-type check --fix                # fix common errors in-place
```

After `setup`, `ty check components/` produces the same diagnostics — zero-config IDE integration via ty LSP.

Exit code **0** — no errors (or no component files found). Exit code **1** — at least one type error detected.

## When not to use this

- **Not a linter** — use [ruff](https://docs.astral.sh/ruff/) for style and formatting issues
- **Only checks `components/**/*.py`** — other Python files in your project are ignored
- **Stub coverage isn't complete** — some batou APIs may not have stubs yet, which can cause false positives. [Report them](https://github.com/flyingcircusio/batou-type/issues)

[Full documentation](docs/user/index.md)
