# Architecture

batou-type has six isolated layers. Each layer owns a single responsibility and follows strict dependency rules. This keeps the core type-checking logic free of framework coupling — both the CLI and the pytest plugin reuse it without pulling in extra dependencies.

## Layer Model

```
cli.py / __main__.py    ← presentation (typer, rich, stogger, structlog)
fixer.py                ← AST transformations (libcst)
output.py               ← output modeling (pydantic)
setup.py                ← project setup (stdlib, structlog, tomli-w)
pytest_plugin.py        ← plugin (pytest)
core.py                 ← domain (stdlib, lazy output import for JSON mode)
vendor/                 ← bundled stubs (leaf, no upward imports)
```

**Dependencies flow strictly downward:**

| Module | Imports from |
|--------|-------------|
| `cli.py` | `fixer.py`, `output.py`, `setup.py`, `core.py` |
| `fixer.py` | `output.py` (`Diagnostic`), libcst |
| `output.py` | `core.py` |
| `setup.py` | (none from batou_type) — stdlib, structlog, tomli-w |
| `pytest_plugin.py` | `core.py` only |
| `core.py` | (none at top-level) — lazy import from `output.py` in `check_file()` |
| `vendor/` | (leaf — no upward imports) |

`pytest-archon` enforces these rules at test time (`tests/test_architecture.py`).

## Framework Isolation

Each layer owns its framework:

| Framework | Where it lives | Why |
|-----------|---------------|-----|
| typer, rich, stogger | `cli.py` only | CLI presentation and diagnostic logging |
| structlog | `__init__.py`, `cli.py`, `setup.py` | Structured logging for version fallback, CLI, and setup operations |
| libcst | `fixer.py` only | AST parsing and transformation for autofix |
| pydantic | `output.py` only | Output structure modeling and JSON serialization |
| pytest | `pytest_plugin.py` only | Plugin hook protocol only |
| stdlib | `core.py` | Domain logic has no framework opinions |
| tomli-w | `setup.py` only | TOML writing (stdlib `tomllib` is read-only) |

`__init__.py` imports structlog for the version fallback log message and re-exports the public API from `core.py`. It never touches typer, rich, stogger, pydantic, or pytest, so importing the public API never triggers the full framework dependency chain.

## Fixer Layer

`fixer.py` sits between the CLI and the output layer. It receives parsed `Diagnostic` objects from the output layer and source code strings, applies AST transformations via libcst, and returns modified source. The CLI calls fixer functions when `--fix`, `--diff`, `--fix-only`, or `--virtual` flags are active.

Each fixer is a `Fixer` dataclass declaring:

- `slug` — identifier for diagnostic matching and logging
- `diagnostic_codes` — `frozenset[str]` of error codes this fixer handles
- `apply(source, diagnostics)` — returns transformed source or `None` if unchanged

The pipeline groups diagnostics by file, matches them to fixers by error code, and applies exactly one fixer per code (no overlap).

Two fixer instances are provided:

- `ADD_MISSING_IMPORT` — handles `possibly-missing-submodule` diagnostics by inserting missing from-imports
- `SELF_DEREF` — handles `unresolved-attribute` diagnostics by transforming `self._` references with walrus operator

## Output Layer

`output.py` bridges the CLI and the domain layer. It builds structured machine-readable output using Pydantic models. The CLI imports it only when JSON mode is active (`--json` / `--output-format json`).

The module contains:

- **Pydantic models** — `CheckOutput` (root), `ProjectResult`, `ComponentResult`, and `Diagnostic` define the JSON output schema. `Diagnostic` is a unified model: converter functions `from_ty_gitlab()` and `from_mypy_jsonl()` map checker-specific formats (GitLab Code Quality, mypy JSONL) to a single structure with `file`, `line`, `column`, `end_line`, `end_column`, `message`, `hint`, `severity`, `code`, and `checker` fields.
- **Serializer** — `build_output()` converts internal `TypeCheckResult` dataclasses from `core.py` into the Pydantic output tree, then serializes to JSON.
- **Schema export** — `export_schema()` exposes the JSON Schema for validation and tooling integration.

The CLI enforces the stdout/stderr split: JSON payload goes to stdout (pipeable), all diagnostic logging goes to stderr via stogger. `output.py` is transport-agnostic — it builds data structures, the CLI decides where they go.

`TypeCheckResult` in `core.py` stays a plain dataclass. Converter functions in the output layer bridge to Pydantic, so the domain layer stays dependency-free.

## Public API Boundary

`__init__.py` defines `__all__` as the stable public surface: `Checker`, `CheckerError`, `TypeCheckResult`, `check_all`, `check_file`, `ensure_checker_available`, `find_components`, and `__version__`. Everything else is an internal implementation detail.

The `output.py` module exports its Pydantic models and `export_schema()` as a programmatic API, but these are **not** re-exported through `__init__.py`. Consumers who need the output models import directly from `batou_type.output`. The CLI is the sole consumer within the package.

Consumers fall into two categories:

- **CLI users** invoke `batou_type.cli:app` via the console script entry point. They never import the package.
- **Library users** (or the pytest plugin) import from `batou_type` or `batou_type.core`. They get the stdlib-only domain layer.

## Vendor Stubs System

batou-type ships bundled `.pyi` type stubs for `batou` and `batou_ext` inside `vendor/`. The CLI discovers stubs at runtime:

1. Check for an **installed** stub package (e.g., `batou-stubs` via pip).
2. If not found, fall back to the **vendored** stubs bundled with batou-type.

This two-tier resolution lets batou-type work out of the box — no separate stub installation needed. Projects can still override with external stubs. The `version` subcommand shows which stubs are loaded and whether they come from the vendor directory or an external package.

The vendored stubs also serve a **migration testing** purpose: installing a newer batou-type with updated stubs in an existing deployment reveals type errors from API changes *before* the actual batou upgrade.

## Entry Points

`pyproject.toml` defines two entry points that connect the package to the outside world:

- **`console_scripts`** — `batou-type` maps to `batou_type.cli:app`, the typer application.
- **`pytest11`** — `batou_type` maps to `batou_type.pytest_plugin`, registering the `--batou-ty` flag.

`__main__.py` is a two-line trampoline: it imports `app` from `cli.py` and calls it, enabling `python -m batou_type`.

## Project Detection

The core module detects batou projects by the presence of a `components/` directory. It also resolves project-level virtual environments (`.venv` for uv, `appenv` for batou) to add their site-packages to the type checker's search path. Detection prefers `.venv` over `appenv` when both exist.
