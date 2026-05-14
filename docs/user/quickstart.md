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
Found 1 project(s)
Checking 3 component(s) in /deploy/my-deployment
app passed type check (ty)
database passed type check (ty)
webserver passed type check (ty)
All 3 component(s) passed
```

## When components have errors

Type errors appear inline. The command exits with code **1**:

```{code-block} text
Found 1 project(s)
Checking 3 component(s) in /deploy/my-deployment
app failed type check (ty)
components/app/component.py:15: error: Cannot access member "misspelled_attribute" on type "Component"
database passed type check (ty)
webserver passed type check (ty)
1 component(s) failed: app

============================================== FAILED COMPONENTS ==============================================
  /deploy/my-deployment: app
============================ 1 component(s) failed type check (ty) ============================
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
