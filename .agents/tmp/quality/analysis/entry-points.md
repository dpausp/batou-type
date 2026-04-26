# Entry Point Inventory

## CLI Subcommands
- `version` — source: src/batou_type/cli.py:69 — description: Show version information (batou-type version + stub package info)
- `check` — source: src/batou_type/cli.py:178 — description: Type-check batou deployment components. Options: --checker/-c (ty/mypy), --verbose/-v, --ty-args

## Scripts / Console Entry Points
- `batou-type` — source: pyproject.toml:23 (`batou_type.cli:app`) — purpose: Main CLI entry point for batou-type type-checking tool
- `python -m batou_type` — source: src/batou_type/__main__.py — purpose: Module execution fallback, delegates to cli.app

## Pytest Plugin Entry Points
- `batou_type` — source: pyproject.toml:26 (`batou_type.pytest_plugin`) — purpose: pytest-11 plugin providing --batou-ty flag for type-checking components during test runs

## Documented Features
- Type checking with ty (default checker) — claimed in: README.md:10 — tested by: test_functional.py::TestCheck::test_check_with_ty_checker
- Type checking with mypy — claimed in: README.md:11 — tested by: test_functional.py::TestCheck::test_check_with_mypy_checker
- Multiple checkers via -c flag — claimed in: README.md:12 — tested by: test_functional.py::TestCheck::test_check_with_ty_checker
- Component discovery (components/**/*.py) — claimed in: README.md:49 — tested by: test_core.py::TestFindComponents, test_functional.py::TestCheck::test_check_nested_components
- Batou project detection (requires components/ dir) — claimed in: README.md:49 — tested by: test_core.py::TestIsBatouProject
- Project venv detection (.venv / appenv) — claimed in: cli.py:133-144 — tested by: test_core.py::TestFindProjectVenv
- Vendored stub packages (batou-stubs, batou_ext-stubs) — claimed in: cli.py:34-37 — tested by: test_functional.py::TestVersion::test_version_shows_stub_info
- Migration testing workflow — claimed in: README.md:39 — tested by: [NO TEST]
- Exit code 0 for no errors / exit code 1 for type errors — claimed in: README.md:26 — tested by: test_functional.py::TestCheck::test_check_clean_component_exits_zero, test_check_component_with_type_error_exits_one
- pytest --batou-ty flag for component type checking — claimed in: pytest_plugin.py — tested by: test_pytest_plugin.py (7 tests)

## Public API (library)
- `batou_type.Checker` — source: src/batou_type/core.py:76 — re-exported from __init__.py
- `batou_type.TypeCheckResult` — source: src/batou_type/core.py:93 — re-exported from __init__.py
- `batou_type.check_all` — source: src/batou_type/core.py:170 — re-exported from __init__.py
- `batou_type.check_file` — source: src/batou_type/core.py:115 — re-exported from __init__.py
- `batou_type.find_components` — source: src/batou_type/core.py:107 — re-exported from __init__.py
- `batou_type.__version__` — source: src/batou_type/__init__.py:23
