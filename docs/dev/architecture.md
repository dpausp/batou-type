# Architecture

batou-type is structured as four isolated layers, each with a single responsibility and strict dependency rules. The separation ensures that the core type-checking logic has zero framework coupling and can be reused from both the CLI and the pytest plugin without pulling in unnecessary dependencies.

## Layer Model

```
cli.py / __main__.py    ← presentation (typer, rich, stogger)
setup.py                ← project setup (stdlib + structlog only)
fixer.py                ← AST transformations (libcst)
output.py               ← output modeling (pydantic)
pytest_plugin.py        ← plugin (pytest)
core.py                 ← domain (stdlib only)
vendor/                 ← bundled stubs (leaf, no upward imports)
```

**Dependency direction is strictly downward.** `cli.py` imports from `setup.py`, `fixer.py`, `output.py`, and `core.py`. `setup.py` is isolated — it imports only stdlib and structlog, with no dependencies on any other `batou_type` module. `fixer.py` imports from `output.py` (the `Diagnostic` model) and libcst. `output.py` imports from `core.py`. `pytest_plugin.py` imports from `core.py` only. Neither `cli.py` nor `pytest_plugin.py` imports the other. `core.py` has no imports from any `batou_type` module — it is self-contained. `vendor/` is a leaf: stub packages sit there for type-checker discovery, nothing in the package imports from `vendor/`.

This is enforced at test time by `pytest-archon` rules in `tests/test_architecture.py`.

## Framework Isolation

Each layer owns its framework:

| Framework | Where it lives | Why |
|-----------|---------------|-----|
| typer, rich, stogger | `cli.py` only | CLI presentation and diagnostic logging |
| structlog | `setup.py` | Structured logging for setup operations |
| libcst | `fixer.py` only | AST parsing and transformation for autofix |
| pydantic | `output.py` only | Output structure modeling and JSON serialization |
| pytest | `pytest_plugin.py` only | Plugin hook protocol only |
| stdlib | `core.py` | Domain logic has no framework opinions |
`__init__.py` re-exports from `core.py` only — it never touches typer, rich, stogger, pydantic, or pytest. This keeps the public API importable without triggering any framework installation.

## Setup Layer

`setup.py` configures a batou deployment project for standalone type checking. It installs stub packages (`batou-stubs`, optionally `batou_ext-stubs`) and the type checker as dev dependencies via `uv add --dev`, then writes minimal `[tool.ty]` configuration to `pyproject.toml`.

After running `batou-type setup`, `ty check components/` produces the same diagnostics as `batou-type check` — enabling zero-config IDE integration via ty LSP.

The module is deliberately isolated from the rest of the package: it imports only stdlib and structlog, with no imports from any `batou_type` module. This keeps it self-contained and testable without pulling in the full dependency chain.

Key functions:

- `run_setup()` — main entry point: detects batou_ext usage, installs packages, writes config
- `_detect_batou_ext_usage()` — scans `components/` for batou_ext imports
- `_run_uv_add()` — subprocess wrapper for `uv add --dev`
- `_write_ty_config()` — appends `[tool.ty]` to pyproject.toml if absent

## Fixer Layer

`fixer.py` sits between the CLI and the output layer. It receives parsed `Diagnostic` objects from the output layer and source code strings, applies AST transformations via libcst, and returns modified source. The CLI calls fixer functions when `--fix`, `--diff`, `--fix-only`, or `--virtual` flags are active.

Each fixer is a `Fixer` dataclass declaring:

- `slug` — identifier for `--fixable` filtering (future use)
- `diagnostic_codes` — `frozenset[str]` of error codes this fixer handles
- `apply(source, diagnostics)` — returns transformed source or `None` if unchanged

The pipeline groups diagnostics by file, matches them to fixers by error code, and applies exactly one fixer per code (no overlap).

## Output Layer

`output.py` sits between the CLI and the domain layer, providing structured machine-readable output via Pydantic models. It is imported by `cli.py` only when JSON mode is active (`--json` / `--output-format json`).

The module contains:

- **Pydantic models** — `CheckOutput` (root), `ProjectResult`, `ComponentResult`, and `Diagnostic` define the JSON output schema. `Diagnostic` is a unified model: converter functions `from_ty_gitlab()` and `from_mypy_jsonl()` map checker-specific formats (GitLab Code Quality, mypy JSONL) to a single structure with `file`, `line`, `column`, `end_line`, `end_column`, `message`, `hint`, `severity`, `code`, and `checker` fields.
- **Serializer** — `build_output()` converts internal `TypeCheckResult` dataclasses from `core.py` into the Pydantic output tree, then serializes to JSON.
- **Schema export** — `export_schema()` exposes the JSON Schema for validation and tooling integration.

The stdout/stderr split is enforced at the CLI layer: JSON payload goes to stdout (pipeable), all diagnostic logging goes to stderr via stogger. `output.py` itself is transport-agnostic — it builds data structures, the CLI decides where they go.

`TypeCheckResult` in `core.py` remains a plain dataclass. The output layer bridges to Pydantic via converter functions, keeping the domain layer dependency-free.

## Public API Boundary

`__init__.py` defines `__all__` as the stable public surface: `Checker`, `TypeCheckResult`, `check_all`, `check_file`, `find_components`, and `__version__`. Everything else is an internal implementation detail.

The `output.py` module exports its Pydantic models and `export_schema()` as a programmatic API, but these are **not** re-exported through `__init__.py`. Consumers who need the output models import directly from `batou_type.output`. The CLI is the sole consumer within the package.
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
