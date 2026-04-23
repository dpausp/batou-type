# Stream A: Code Architecture

## Verdict: RED

## Architecture Tests

**`tests/test_architecture.py` does not exist.** The baseline test run confirms:

```
ERROR: file or directory not found: tests/test_architecture.py
```

No pytest-archon, no import-layer rules, no dependency-direction enforcement.

## Architecture Documentation

The entry-points inventory reveals a clear module structure:

| Module | Responsibility |
|---|---|
| `core.py` | Business logic: `Checker` enum, `TypeCheckResult`, `check_file`, `check_all`, `find_components`, subprocess invocation |
| `cli.py` | Presentation: Typer app, Rich output, `version` and `check` subcommands |
| `pytest_plugin.py` | Test framework integration: `--batou-ty` flag, `BatouComponentFile`/`BatouComponentItem` collectors |
| `__init__.py` | Re-export layer: re-exports `core.py` public API, defines `__version__` |
| `__main__.py` | Entry point delegation: imports `app` from `cli.py` |

## Is Architecture Enforced?

**No.** The only tests are in `test_refactor_contract.py`, which validates *structural contracts* (file exists, module has no typer import, AST shape checks). These are **refactoring guards**, not architecture enforcement.

What's missing:
- No import-direction rules (e.g., `cli.py` must not import from `pytest_plugin.py`)
- No layer-boundary checks (core should be CLI/framework-agnostic)
- No dependency-inversion enforcement
- No cyclomatic complexity rules

**Architecture exists as convention only, not as enforced constraint.**

## Risk

The current module boundaries are clean in practice — `core.py` has no Typer/Rich imports, `cli.py` wraps `core.py`, `pytest_plugin.py` wraps `core.py`. But nothing prevents a future commit from adding a `from batou_type.cli import app` inside `core.py`, inverting the dependency.
