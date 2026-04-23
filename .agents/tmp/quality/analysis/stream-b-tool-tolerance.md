# Stream B: Code Quality — Tool Tolerance Audit

## Verdict: ORANGE

## Ruff: Project Config (baseline) vs Full Ruleset (extreme)

### Project Config

```
All checks passed!
```

The project has **zero ruff configuration** — no `[tool.ruff]` in pyproject.toml, no `.ruff.toml`. The default ruff ruleset is extremely permissive. "All checks passed" means only the barest builtin rules are active.

### Full Ruleset: 84 errors found

#### Legitimate Suppressions (project decisions)

| Rule | Count | Category | Notes |
|---|---|---|---|
| CPY001 | 5 | Copyright notices | No copyright headers — legitimate project choice |
| S101 | 14 | Assert in tests | Standard suppression for test files |
| D100/D101/D102/D103/D104/D107 | 9 | Docstrings | Style preference, not quality |
| DOC201/DOC501 | 6 | Docstring completeness | Return/exception documentation |
| COM812 | 3 | Trailing commas | Formatter conflict territory |
| RUF022 | 1 | `__all__` sorting | Cosmetic |
| RUF067 | 1 | `__init__` purity | Stylistic concern |

**Subtotal: ~39 legitimate**

#### Questionable (quality issues being hidden)

| Rule | Count | Location | Issue |
|---|---|---|---|
| E501 | 2 | `cli.py:54`, `cli.py:67` | Line length violations in Rich formatting strings — real formatting issue |
| PLW1510 | 2 | `core.py:74`, `core.py:81` | `subprocess.run` without explicit `check=False` — silent error swallowing risk |
| BLE001 | 1 | `cli.py:41` | `except Exception` — blind exception catch in `get_stub_versions()` |
| PERF203 | 1 | `cli.py:41` | try/except inside loop — the blind catch is inside a loop, compounding the problem |
| ANN002/ANN003/ANN201/ANN204 | 7+ | Various | Missing type annotations — these are in tests AND source |
| PLC0415 | 2 | `pytest_plugin.py:92`, test file | Non-top-level imports |
| I001 | 1 | `pytest_plugin.py:3` | Unsorted imports |
| RUF100 | 4 | `test_refactor_contract.py` | Unused noqa directives — dead noqa comments |

**Subtotal: ~20 questionable**

#### Critical Hiding (serious problems suppressed)

| Rule | Count | Location | Issue |
|---|---|---|---|
| S404 | 1 | `core.py:5` | `subprocess` import flagged as potentially insecure |
| S603 | 2 | `core.py:74`, `core.py:81` | `subprocess.run` with untrusted input — the tool executes user-provided checker commands |
| B008 | 1 | `cli.py:106` | Function call in argument default (`typer.Option()`) — Typer convention, but flagged for awareness |

**Subtotal: ~4 critical-level**

The S404/S603 findings are the most concerning. `core.py` constructs and executes subprocess commands. The command construction uses `sys.executable` (safe) and `CHECKER_COMMANDS` (hardcoded), but `file_path` comes from filesystem glob results. No shell injection risk currently, but this pattern deserves awareness.

### Noqa Density

**Zero noqa comments found.** The `extreme/noqa-comments.txt` is empty. Clean.

### Type Ignores

**1 type: ignore found** in `cli.py:40`:
```python
stub_path = str(files(pkg).joinpath("lib").parent)  # type: ignore[unresolved-attribute]
```

This is **properly scoped** with `[unresolved-attribute]` error code. Not a bare `# type: ignore`. Legitimate — `importlib.resources.files()` returns `Traversable` which doesn't expose `.parent` in all type stubs.

## Ty Type Checker

```
All checks passed!
```

Clean. No type errors detected.

## Signal Summary

| Tool | Project Config | Full Ruleset | Signal |
|---|---|---|---|
| ruff | 0 issues (defaults only) | 84 issues | **ORANGE** — no config means most rules silently skipped |
| ty | All clean | N/A | **GREEN** |
| noqa density | 0 | N/A | **GREEN** |
| type:ignore | 1 (scoped) | N/A | **GREEN** |

## Key Finding

The project has **zero ruff configuration**. This is not "clean code" — it's "no rules applied." The 84 errors from the full ruleset include genuine quality concerns (blind exception catches, subprocess security, missing annotations) that are invisible in daily development.
