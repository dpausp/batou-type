# batou_type

**Generated:** 2026-05-05

See ../../docs/dev/architecture.md for full architecture reference (layer model, framework isolation, dependency rules).

## Entry Points

- `__init__.py` — Public API: `Checker`, `TypeCheckResult`, `check_all`, `check_file`, `find_components`, `__version__`
- `__main__.py` — `python -m batou_type` trampoline → `cli.py`
- `cli.py` — Typer app with `version`, `check`, and `setup` commands; uses stogger for logging, rich for output
- `setup.py` — Project setup: installs stub packages + type checker as dev deps. Stdlib + structlog only.
- `core.py` — Domain: project detection (components/ dir), venv resolution, checker subprocess invocation. Stdlib-only.
- `output.py` — Pydantic models (`CheckOutput`, `Diagnostic`), converters (`from_ty_gitlab`, `from_mypy_jsonl`), `build_output`, `export_schema`
- `fixer.py` — libcst-based autofix: `ADD_MISSING_IMPORT`, `SELF_DEREF` fixer instances. Imports from `output.py` only.
- `pytest_plugin.py` — Registers `--batou-ty` flag; `BatouComponentItem`/`BatouComponentFile` for per-component type checking

## Architecture Rules (enforced by pytest-archon)

- `core.py` → no imports from any batou_type module or framework
- `setup.py` → no imports from any batou_type module (stdlib + structlog only)
- `output.py` → imports from `core.py` only
- `fixer.py` → imports from `output.py` only; no frameworks (typer, rich, pytest, structlog, stogger banned)
- `cli.py` → imports from `setup.py`, `core.py`, `output.py`, and `fixer.py` only
- `pytest_plugin.py` → imports from `core.py` only
- `cli.py` ⟷ `pytest_plugin.py` → never import each other
- `setup.py` ⟷ `pytest_plugin.py` → never import each other
