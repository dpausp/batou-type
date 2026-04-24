# Entry Point Inventory

## CLI Subcommands

| Command | Source | Description |
|---|---|---|
| `check` | `src/batou_type/cli.py:155` | Type-check batou deployment components |
| `version` | `src/batou_type/cli.py:58` | Show version information |

### `check` command options

| Option | Type | Default | Source | Description |
|---|---|---|---|---|
| `paths` (positional) | `list[Path]` | `[Path.cwd()]` | `cli.py:156-159` | Project directories to check |
| `--checker` / `-c` | `list[Checker] \| None` | `None` (falls back to `[Checker.ty]`) | `cli.py:160-165` | Type checker(s) to run |

Internal helper:
- `_run_check()` at `cli.py:68` — orchestrates project discovery, venv detection, stub loading, and result reporting. Called by `check`.

### `version` command

No options. Prints `batou-type` version plus stub package versions and paths.

## Scripts / Console Entry Points

| Script | Entry Point | Source | Purpose |
|---|---|---|---|
| `batou-type` | `batou_type.cli:app` | `pyproject.toml:23` | Main CLI via `project.scripts` |
| `python -m batou_type` | `__main__.py:1-3` (calls `batou_type.cli:app`) | `src/batou_type/__main__.py` | Module-executable entry point |

Both invoke the same Typer `app` instance.

## Documented Features

### From `README.md`

| Feature | Claimed In | Tested By |
|---|---|---|
| Type-check batou deployment components against batou stubs | `README.md:3` | `test_functional.py:TestCheck` |
| Discovers all `components/**/*.py` files | `README.md:5` | `test_functional.py:test_check_nested_components` |
| Supports `ty` checker (default) | `README.md:10,33` | `test_functional.py:test_check_with_ty_checker` |
| Supports `mypy` checker | `README.md:11,34` | `test_functional.py:test_check_with_mypy_checker` |
| Supports `basedpyright` checker | `README.md:12,35` | **Not implemented** — `Checker` enum in `core.py:38-40` only has `ty` and `mypy` |
| Run multiple checkers in sequence (`-c` repeated) | `README.md:13,37` | No explicit multi-checker test |
| Status messages to stderr, checker output to stdout | `README.md:18-26` | `test_functional.py` verifies stdout/stderr behavior |
| Exit code 0 on no errors or no component files | `README.md:27` | `test_functional.py:test_check_no_components_exits_zero`, `test_check_clean_component_exits_zero` |
| Exit code 1 on type errors | `README.md:27` | `test_functional.py:test_check_component_with_type_error_exits_one` |
| Migration testing (preview breaking changes) | `README.md:41-47` | No test |
| Standard batou deployment layout detection | `README.md:51-61` | `test_functional.py` via `temp_project` fixture |
| Automatic basedpyright noise filtering | `README.md:35` | **Not implemented** in `core.py` |
| mypy `--explicit-package-bases --check-untyped-defs --no-incremental` | `README.md:34` | `core.py:44-51` defines these flags |

### From module docstrings

| Feature | Claimed In |
|---|---|
| "Type-check batou deployments" | `src/batou_type/__init__.py:1` |
| "Batou type CLI" | `src/batou_type/cli.py:1` |
| "Core type checking logic shared between CLI and pytest plugin" | `src/batou_type/core.py:1` |
| "Batou type checking plugin for pytest" | `src/batou_type/pytest_plugin.py:1` |

### Discrepancy: `basedpyright` documented but not implemented

`README.md:12,35` and `testproject/README.md:31,38-39` document `basedpyright` as a supported checker. However, the `Checker` enum in `core.py:38-40` only defines `ty` and `mypy`. The `CHECKER_COMMANDS` dict in `core.py:43-51` has no `basedpyright` entry. The `-c basedpyright` flag would fail at Typer's enum validation.

## Public API (if library)

### `__all__` exports from `src/batou_type/__init__.py:13-20`

| Symbol | Origin | Source | Description |
|---|---|---|---|
| `Checker` | `batou_type.core` | `core.py:38` | Enum of supported type checkers (`ty`, `mypy`) |
| `TypeCheckResult` | `batou_type.core` | `core.py:55` | Dataclass: `path: str`, `has_errors: bool`, `output: str` |
| `check_all` | `batou_type.core` | `core.py:119` | Type-check all components in a deployment root |
| `check_file` | `batou_type.core` | `core.py:76` | Run type checker(s) on a single file |
| `find_components` | `batou_type.core` | `core.py:68` | Find all `components/**/*.py` files under a root |
| `__version__` | `batou_type.__init__` | `__init__.py:23` | Package version from `importlib.metadata.version()` |

### Public symbols in `core.py` NOT in `__all__`

These are importable from `batou_type.core` but not re-exported via `batou_type.__init__`:

| Symbol | Source | Used By | Description |
|---|---|---|---|
| `find_project_venv` | `core.py:13` | `cli.py:20` | Detect project-level venv (`.venv` or `appenv`) |
| `get_venv_site_packages` | `core.py:24` | `cli.py:21` | Extract site-packages paths from a venv |
| `is_batou_project` | `core.py:63` | `cli.py:21` | Check if directory has a `components/` subdirectory |
| `CHECKER_COMMANDS` | `core.py:43` | `core.py:99` | Map of Checker to CLI command arguments |

### Internal-only symbols in `cli.py`

| Symbol | Source | Description |
|---|---|---|
| `app` | `cli.py:24` | Typer application instance |
| `console` | `cli.py:28` | Rich Console instance |
| `STUB_PACKAGES` | `cli.py:30` | List of stub package names |
| `StubInfo` | `cli.py:34` | Dataclass for stub version metadata |
| `get_stub_versions` | `cli.py:42` | Collect version/path for stub packages |
| `_run_check` | `cli.py:68` | Internal orchestrator for the `check` command |

## Pytest Plugin Hooks

**Entry point**: `batou_type = "batou_type.pytest_plugin"` (`pyproject.toml:26`)

| Hook | Source | Description |
|---|---|---|
| `pytest_addoption` | `pytest_plugin.py:14` | Adds `--batou-ty` CLI flag under the "batou" option group |
| `pytest_configure` | `pytest_plugin.py:23` | Registers the `batou_ty` marker |
| `pytest_collect_file` | `pytest_plugin.py:27` | Collects `components/**/*.py` files as `BatouComponentFile` items (only when `--batou-ty` is active) |
| `pytest_collection_modifyitems` | `pytest_plugin.py:43` | Runs `check_all()` upfront for the entire project, stashes results in `config.stash` for test items to read |

### Pytest plugin classes

| Class | Source | Description |
|---|---|---|
| `BatouComponentFile` | `pytest_plugin.py:66` | `pytest.File` subclass — collects a batou component `.py` file |
| `BatouComponentItem` | `pytest_plugin.py:73` | `pytest.Item` subclass — runs the type-check assertion for one file; reads stashed results, fails with diagnostic count if errors |

### Stash keys

| Key | Source | Type | Description |
|---|---|---|---|
| `_BATOU_TY_RESULTS_STASH_KEY` | `pytest_plugin.py:10` | `dict[str, bool]` | Maps file path to `has_errors` |
| `_BATOU_TY_OUTPUT_STASH_KEY` | `pytest_plugin.py:11` | `dict[str, str]` | Maps file path to checker output |

## Configuration Surface

### CLI flags (Typer options on `check` command)

| Name | Type | Default | Source | Description |
|---|---|---|---|---|
| `paths` | `list[Path]` (positional) | `[cwd]` | `cli.py:156-159` | Project directories to check; non-project dirs are scanned for subdirectories that are batou projects |
| `--checker` / `-c` | `list[Checker]` (repeatable) | `[Checker.ty]` | `cli.py:160-165` | Which type checker(s) to run; values: `ty`, `mypy` |

### CLI flags (Typer options on `version` command)

No options.

### Pytest plugin options

| Name | Type | Default | Source | Description |
|---|---|---|---|---|
| `--batou-ty` | `bool` (store_true) | `False` | `pytest_plugin.py:16-19` | Enable batou type checking; activates component file collection and type-check test items |

### Pytest markers

| Marker | Source | Description |
|---|---|---|
| `batou_ty` | `pytest_plugin.py:24` | Applied to all `BatouComponentItem` instances |

### Pyright configuration (`pyrightconfig.json`)

| Setting | Value | Description |
|---|---|---|
| `pythonVersion` | `"3.14"` | Target Python version for type checking |
| `typeCheckingMode` | `"strict"` | Strict mode |
| `reportExplicitAny` | `"none"` | Suppress explicit-any warnings |
| `reportAny` | `"none"` | Suppress any-type warnings |
| `reportMissingTypeStubs` | `true` | Warn on missing stubs |
| `reportImplicitOverride` | `"none"` | Suppress implicit-override warnings |
| `reportInvalidTypeArguments` | `"none"` | Suppress invalid-type-arg warnings |
| `reportIncompatibleMethodOverride` | `"none"` | Suppress method-override warnings |
| `reportIncompatibleVariableOverride` | `"none"` | Suppress variable-override warnings |
| `reportOverlappingOverload` | `"none"` | Suppress overlapping-overload warnings |
| `reportAttributeAccessIssue` | `"none"` | Suppress attribute-access warnings |

This is the config for type-checking batou-type itself (not the projects it checks). Many strict-mode diagnostics are suppressed.

### Hardcoded configuration in `core.py`

| Setting | Value | Source | Description |
|---|---|---|---|
| `_VENV_CANDIDATES` | `[".venv", "appenv"]` | `core.py:10` | Venv directory names to probe, in priority order |
| `CHECKER_COMMANDS[Checker.ty]` | `["ty", "check"]` | `core.py:44` | Ty CLI invocation |
| `CHECKER_COMMANDS[Checker.mypy]` | `["mypy", "--explicit-package-bases", "--check-untyped-defs", "--no-incremental"]` | `core.py:45-51` | Mypy CLI invocation with batou-specific flags |
| `STUB_PACKAGES` | `["batou-stubs", "batou_ext-stubs"]` | `cli.py:30` | Stub packages whose versions are displayed |

### Ty `--extra-search-path` (dynamic)

When a project venv is detected, its `site-packages` directories are passed to `ty check --extra-search-path` for each component file (`core.py:93-94`). This is not a user-facing config option — it is derived from filesystem state.
