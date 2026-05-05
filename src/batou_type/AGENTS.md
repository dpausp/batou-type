# batou_type

**Generated:** 2026-04-29

See ../../docs/dev/architecture.md for full architecture reference (layer model, framework isolation, dependency rules).

## Entry Points

- `__init__.py` — Public API: `Checker`, `TypeCheckResult`, `check_all`, `check_file`, `find_components`, `__version__`
- `__main__.py` — `python -m batou_type` trampoline → `cli.py`
- `cli.py` — Typer app with `version` and `check` commands; uses stogger for logging, rich for output
- `core.py` — Domain: project detection (components/ dir), venv resolution, checker subprocess invocation. Stdlib-only.
- `output.py` — Pydantic models (`CheckOutput`, `Diagnostic`), converters (`from_ty_gitlab`, `from_mypy_jsonl`), `build_output`, `export_schema`
- `pytest_plugin.py` — Registers `--batou-ty` flag; `BatouComponentItem`/`BatouComponentFile` for per-component type checking

## Architecture Rules (enforced by pytest-archon)

- `core.py` → no imports from any batou_type module or framework
- `cli.py` → imports from `core.py` and `output.py` only
- `output.py` → imports from `core.py` only
- `pytest_plugin.py` → imports from `core.py` only
- `cli.py` ⟷ `pytest_plugin.py` → never import each other
