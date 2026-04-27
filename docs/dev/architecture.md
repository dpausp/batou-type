# Architecture

batou-type is structured as three isolated layers, each with a single responsibility and strict dependency rules. The separation ensures that the core type-checking logic has zero framework coupling and can be reused from both the CLI and the pytest plugin without pulling in unnecessary dependencies.

## Layer Model

```
cli.py / __main__.py    ← presentation (typer, rich)
pytest_plugin.py        ← plugin (pytest)
core.py                 ← domain (stdlib only)
vendor/                 ← bundled stubs (leaf, no upward imports)
```

**Dependency direction is strictly downward.** `cli.py` and `pytest_plugin.py` both import from `core.py`. Neither imports the other. `core.py` has no imports from any `batou_type` module — it is self-contained. `vendor/` is a leaf: stub packages sit there for type-checker discovery, nothing in the package imports from `vendor/`.

This is enforced at test time by `pytest-archon` rules in `tests/test_architecture.py`.

## Framework Isolation

Each layer owns its framework:

| Framework | Where it lives | Why |
|-----------|---------------|-----|
| typer, rich | `cli.py` only | CLI presentation concerns only |
| pytest | `pytest_plugin.py` only | Plugin hook protocol only |
| stdlib | `core.py` | Domain logic has no framework opinions |

`__init__.py` re-exports from `core.py` only — it never touches typer, rich, or pytest. This keeps the public API importable without triggering any framework installation.

## Public API Boundary

`__init__.py` defines `__all__` as the stable public surface: `Checker`, `TypeCheckResult`, `check_all`, `check_file`, `find_components`, and `__version__`. Everything else is an internal implementation detail.

Consumers fall into two categories:

- **CLI users** invoke `batou_type.cli:app` via the console script entry point. They never import the package.
- **Library users** (or the pytest plugin) import from `batou_type` or `batou_type.core`. They get the stdlib-only domain layer.

## Vendor Stubs System

batou-type ships bundled `.pyi` type stubs for `batou` and `batou_ext` inside `vendor/`. The CLI discovers stubs at runtime:

1. Check for an **installed** stub package (e.g., `batou-stubs` via pip).
2. If not found, fall back to the **vendored** stubs bundled with batou-type.

This two-tier resolution means batou-type works out-of-the-box without requiring separate stub installations, while allowing projects to override with external stubs if needed. The `version` subcommand shows which stubs are loaded and whether they are vendored or external.

The vendored stubs also serve a **migration testing** purpose: installing a newer batou-type with updated stubs in an existing deployment reveals type errors from API changes *before* the actual batou upgrade.

## Entry Points

Two setuptools entry points connect the package to the outside world:

- **`console_scripts`** — `batou-type` maps to `batou_type.cli:app`, the typer application.
- **`pytest11`** — `batou_type` maps to `batou_type.pytest_plugin`, registering the `--batou-ty` flag.

`__main__.py` is a two-line trampoline: it imports `app` from `cli.py` and calls it, enabling `python -m batou_type`.

## Project Detection

The core module detects batou projects by the presence of a `components/` directory. It also resolves project-level virtual environments (`.venv` for uv, `appenv` for batou) to add their site-packages to the type checker's search path. Detection prefers `.venv` over `appenv` when both exist.
