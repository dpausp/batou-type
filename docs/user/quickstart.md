# Quickstart

Type-check your batou deployment components to catch errors before deploying.

## Prerequisites

- A batou deployment with a `components/` directory
- `batou-type` installed in the same environment as your deployment

## Run Your First Check

```{code-block} shell
$ batou-type check
```

This discovers all `components/**/*.py` files in the current directory and type-checks them with [ty](https://github.com/astral-sh/ty) (the default checker).

You will see output like this:

```{code-block} text
Loaded stubs:
  batou-stubs vendored @ /path/to/stubs
  batou_ext-stubs vendored @ /path/to/stubs
Python: /path/to/python

Found 1 project(s):
  /path/to/my-deployment

Checking 3 component(s) in /path/to/my-deployment...

All components passed type checking.
```

## What Happens When There Are Errors

When a component has type errors, `batou-type` prints the diagnostics and exits with code 1:

```{code-block} text
components/app/component.py:15: error: Cannot access member "misspelled_attribute" on type "Component"
Found 1 diagnostic

================================ FAILED COMPONENTS ================================
  /path/to/my-deployment: app
============================ 1 component(s) failed type check (ty) ============================
```

Fix the reported issues in your components and re-run until all checks pass.

## Check a Specific Directory

```{code-block} shell
$ batou-type check /path/to/deployment
```

You can pass multiple directories. If a directory is not itself a batou project, `batou-type` scans its subdirectories for projects.

## Next Steps

- [Usage](usage.md) — checker selection, pytest integration, migration testing
