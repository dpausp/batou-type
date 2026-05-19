# Quickstart

Type-check your batou deployment components to catch errors before deploying.

## Prerequisites

- A batou deployment with a `components/` directory containing Python files
- `batou-type` installed (`uv add --dev batou-type` or `pip install batou-type`)

The default type checker ([ty](https://github.com/astral-sh/ty)) is installed automatically as a dependency.

## Run your first check

From inside your deployment directory:

```{code-block} shell
$ batou-type check
```

Discovers all `components/**/*.py` files and type-checks them with ty.

Expected output when all components pass:

```{code-block} text
2026-05-19T20:03:12Z I projects-found                 Found 1 project(s)
2026-05-19T20:03:12Z I checking-components            Checking 1 component(s) in /deploy/my-deployment
2026-05-19T20:03:13Z I component-passed               myapp passed type check (ty)
2026-05-19T20:03:13Z I components-passed              All 1 component(s) passed
```

Output uses structured logging: ISO timestamps, severity (`I` = info, `W` = warning, `E` = error), and event names. In a terminal, errors appear in red.

## When components have errors

Type errors appear inline. The command exits with code **1**:

```{code-block} text
2026-05-19T20:03:27Z I projects-found                 Found 1 project(s)
2026-05-19T20:03:27Z I checking-components            Checking 3 component(s) in /deploy/my-deployment
2026-05-19T20:03:27Z E component-errors               app failed type check (ty)
error-project/app: error[invalid-argument-type]: Argument to `Address.__init__` is incorrect
error-project/app:   --> components/app/component.py:10:29
error-project/app:    |
error-project/app: 10 |         self.addr = Address(42, 8080)
error-project/app:    |                             ^^ Expected `str`, found `Literal[42]`
error-project/app:    |
2026-05-19T20:03:27Z I component-passed               database passed type check (ty)
2026-05-19T20:03:27Z I component-passed               webserver passed type check (ty)
2026-05-19T20:03:27Z W components-failed              1 component(s) failed: app
2026-05-19T20:03:27Z E components-failed-header         FAILED COMPONENTS
2026-05-19T20:03:27Z E components-failed-project        /deploy/my-deployment: app
2026-05-19T20:03:27Z E components-failed-summary        1 component(s) failed type check (ty)
```

Fix the reported issues and re-run until all checks pass.

## Check a specific directory

```{code-block} shell
$ batou-type check /path/to/deployment
```

Pass multiple paths to check several directories. When a directory is not itself a batou project, `batou-type` scans its subdirectories for projects with a `components/` directory.

## Next steps

- [Autofix](autofix.md) — preview and apply automatic fixes
- [pytest integration](pytest.md) — add type checks to your test suite
- [Reference](reference.md) — all flags, exit codes, JSON format
- Run `batou-type setup` once for IDE-native type checking (zero-config `ty check components/`)
