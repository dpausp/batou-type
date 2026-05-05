# Architecture

batou-type is structured as four isolated layers, each with a single responsibility and strict dependency rules. The separation ensures that the core type-checking logic has zero framework coupling and can be reused from both the CLI and the pytest plugin without pulling in unnecessary dependencies.

## Layer Model

```
cli.py / __main__.py    ← presentation (typer, rich, stogger)
fixer.py                ← autofix transforms (libcst)
output.py               ← output modeling (pydantic)
pytest_plugin.py        ← plugin (pytest)
core.py                 ← domain (stdlib + lazy output import)
vendor/                 ← bundled stubs (leaf, no upward imports)
```

**Dependency direction is strictly downward.** `cli.py` imports from `fixer.py`, `output.py`, and `core.py`. `fixer.py` imports from `output.py` (the `Diagnostic` model) and libcst — it does not import from `core.py` directly. `output.py` imports from `core.py`. `pytest_plugin.py` imports from `core.py` only. Neither `cli.py` nor `pytest_plugin.py` imports the other. `core.py` has no top-level runtime imports from any `batou_type` module — it lazily imports from `output.py` only inside `check_file()` when JSON diagnostics need parsing. `vendor/` is a leaf: stub packages sit there for type-checker discovery, nothing in the package imports from `vendor/`.

This is enforced at test time by `pytest-archon` rules in `tests/test_architecture.py`.

## Framework Isolation

Each layer owns its framework:

| Framework | Where it lives | Why |
|-----------|---------------|-----|
| typer, rich, stogger | `cli.py` only | CLI presentation and diagnostic logging |
| libcst | `fixer.py` only | AST transformation for autofix |
| pydantic | `output.py` only | Output structure modeling and JSON serialization |
| pytest | `pytest_plugin.py` only | Plugin hook protocol only |
| structlog | `cli.py`, `__init__.py` | Structured logging for diagnostics and version fallback |
| stdlib | `core.py` | Domain logic has no framework opinions |
`__init__.py` re-exports from `core.py` only — it never touches typer, rich, stogger, pydantic, or pytest. It does import `structlog` for version-fallback logging when the package is not installed. This keeps the public API importable without triggering any framework installation beyond the logging dependency.

## Output Layer

`output.py` sits between the CLI and the domain layer, providing structured machine-readable output via Pydantic models. The `Diagnostic` model is imported unconditionally by `cli.py` and `fixer.py` at module level. `build_output()` and `export_schema()` are conditionally imported by `cli.py` only when JSON mode is active (`--json` / `--output-format json`) or schema export is requested (`--show-schema`).

The module contains:

- **Pydantic models** — `CheckOutput` (root), `ProjectResult`, `ComponentResult`, and `Diagnostic` define the JSON output schema. `Diagnostic` is a unified model: converter functions `from_ty_gitlab()` and `from_mypy_jsonl()` map checker-specific formats (GitLab Code Quality, mypy JSONL) to a single structure with `file`, `line`, `column`, `end_line`, `end_column`, `message`, `hint`, `severity`, `code`, and `checker` fields.
- **Serializer** — `build_output()` converts internal `TypeCheckResult` dataclasses from `core.py` into the Pydantic output tree, then serializes to JSON.
- **Schema export** — `export_schema()` exposes the JSON Schema for validation and tooling integration.

The stdout/stderr split is enforced at the CLI layer (see [](#logging-design)). `output.py` itself is transport-agnostic — it builds data structures, the CLI decides where they go.

`TypeCheckResult` in `core.py` remains a plain dataclass. The output layer bridges to Pydantic via converter functions, keeping the dataclass free of Pydantic dependencies — the domain layer's only runtime import from `output.py` is the lazy one inside `check_file()`.

## Fixer Layer

`fixer.py` sits between the CLI and the output layer, providing automated source-code fixes for mechanically repairable diagnostics. It uses libcst for AST-preserving transformations (formatting and comments are retained).

The module defines a `Fixer` dataclass protocol: each fixer declares `slug` and `diagnostic_codes` (the error codes it handles), and exposes an `apply(source, diagnostics) -> str | None` function. The pipeline routes diagnostics to fixers by code — one code maps to exactly one fixer.

Two fixers exist:

- **add-missing-import** — handles `possibly-missing-submodule` diagnostics. Extracts the module path from the diagnostic, checks for existing imports via libcst, and either merges into an existing `from X import ...` or inserts a new import at the top of the file.
- **self-deref** — handles `self._` dereferencing on `Component | None`. Transforms `self += X` to `self += (_ := X)` (walrus) only when `self._` is actually referenced in the same scope, and replaces `self._` access with `_`.

`fixer.py` imports from `output.py` (the `Diagnostic` model) and libcst. It must not import from `cli.py`, `core.py`, or any framework module (typer, rich, pytest, structlog). This keeps the fixer testable in isolation with just libcst and the output models.

The CLI dispatches to `run_fix()` when any fix flag is set (`--fix`, `--diff`, `--fix-only`). `run_fix()` reuses `check_all(json_mode=True)` to get diagnostics, groups them by file, and applies the matching fixers. The fix pipeline is separate from `run_check()` — the read-only lint path remains unchanged.

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

## Logging Design

All diagnostic output uses structlog via the stogger convention layer. Events follow a strict separation:

- **`log.info`** — user-visible messages. Every call requires `_replace_msg` for human-readable output. These appear on stderr in default mode.
- **`log.warning`** — noteworthy conditions the user should see (e.g., no projects found). Also requires `_replace_msg`.
- **`log.debug`** — internal diagnostics (stub resolution, venv detection, version fallback). Only visible with `-v`.

Context binding (`log.bind(project=...)`) is used for keys that repeat 3+ times within a function scope, avoiding redundant kwargs on individual calls.

The stdout/stderr split is enforced at the CLI layer: JSON payload goes to stdout (pipeable), all diagnostic logging goes to stderr. `output.py` is transport-agnostic.
