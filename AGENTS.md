# batou-type

**Generated:** 2026-04-29

Type-check batou deployment components against batou stubs.

## Documentation

- docs/dev/architecture.md — Four-layer model, framework isolation, entry points, vendor stubs system, public API boundary
- docs/dev/testing.md — Test pyramid (0% mock ratio), test file roles, architecture enforcement
- docs/user/quickstart.md — Getting started, first type-check run
- docs/user/usage.md — Checker selection, JSON output, pytest integration, migration testing
- docs/autoapi/ — Auto-generated API reference (Sphinx autoapi)
- README.md — CLI usage, output format, migration testing workflow

## Stack

Python ≥3.13 · hatchling (build) · uv (package manager) · tox (task runner) · Sphinx + Furo + MyST (docs)

## Commands

- Install: `uv sync`
- Test: `tox -e cov` or `pytest`
- Lint/fix: `tox -e fix`
- Docs: `tox -e docs`
- Type check: `ty` (primary), `mypy` (optional via `batou-type[mypy]`)

## Structure

    src/batou_type/     Main package — 6 modules + vendor/ stubs
      core.py            Domain logic (stdlib-only)
      cli.py             Typer CLI (version, check commands)
      output.py          Pydantic models, JSON output
      fixer.py           libcst-based autofix for common diagnostics
      pytest_plugin.py   pytest --batou-ty integration
      vendor/            Bundled .pyi stubs for batou + batou_ext
    tests/              8 test files (unit, integration, E2E, architecture)
    docs/               Sphinx source (user guide, dev guide, API ref)
    examples/           Sample batou deployments (clean, error, mixed)
    pyproject.toml      All config: build, deps, ruff, ty, tox

## Conventions

- src/ layout, public API via `__all__` in `__init__.py`
- Four-layer architecture enforced by pytest-archon at test time
- 0% mock ratio — all tests hit real code paths (tmp_path, pytester, subprocess)
- Ruff excludes: examples/, testproject/, src/batou_type/vendor/
- Stubs synced from sibling repos via `update-stubs.sh`
