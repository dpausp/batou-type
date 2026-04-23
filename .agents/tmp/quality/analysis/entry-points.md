# Entry Point Inventory

## CLI Subcommands

- `check` — source: [src/batou_type/cli.py:104](src/batou_type/cli.py#L104) — description: "Type-check batou deployment components." Options: `--checker` / `-c` (repeatable, default: `ty`)
- `version` — source: [src/batou_type/cli.py:48](src/batou_type/cli.py#L48) — description: "Show version information." (prints batou-type version + stub package versions/paths)

Notes:
- The Typer app is configured with `no_args_is_help=True`, so running bare `batou-type` shows help.
- The README documents usage as `batou-typecheck` (the README title says "batou-typecheck") but the actual console script entry point is named `batou-type` (see pyproject.toml line 24). This is a naming inconsistency.
- README examples show `batou-typecheck` as the command name, not `batou-type`.
- The default subcommand is not set; users must explicitly use a subcommand (`check`, `version`).

## Scripts / Console Entry Points

- `batou-type` — source: [pyproject.toml:24](pyproject.toml#L24) — purpose: CLI entry point, maps to `batou_type.cli:app` (Typer app)
- `pytest11: batou_type` — source: [pyproject.toml:26-27](pyproject.toml#L26) — purpose: pytest plugin entry point, maps to `batou_type.pytest_plugin`. Registers the `--batou-ty` CLI flag and `batou_ty` marker.

## Public API (Library)

Exported via `__all__` in [src/batou_type/__init__.py](src/batou_type/__init__.py):

- `batou_type.Checker` — source: [src/batou_type/core.py:12](src/batou_type/core.py#L12) — `str, Enum` with values: `ty`, `mypy`, `basedpyright`
- `batou_type.TypeCheckResult` — source: [src/batou_type/core.py:30](src/batou_type/core.py#L30) — `@dataclass` with fields: `path: str`, `has_errors: bool`, `output: str`
- `batou_type.check_all` — source: [src/batou_type/core.py:96](src/batou_type/core.py#L96) — `(root: Path, checkers: list[Checker] | None = None) -> list[TypeCheckResult]`
- `batou_type.check_file` — source: [src/batou_type/core.py:47](src/batou_type/core.py#L47) — `(file_path: str, checkers: list[Checker] | None = None, cwd: Path | None = None) -> TypeCheckResult`
- `batou_type.find_components` — source: [src/batou_type/core.py:39](src/batou_type/core.py#L39) — `(root: Path) -> list[Path]` — globs `components/**/*.py`
- `batou_type.__version__` — source: [src/batou_type/__init__.py:22](src/batou_type/__init__.py#L22) — from `importlib.metadata.version("batou-type")`, fallback `"0.0.0"`

Internal (not in `__all__`, but importable):
- `batou_type.core.CHECKER_COMMANDS` — source: [src/batou_type/core.py:18](src/batou_type/core.py#L18) — `dict[Checker, list[str]]` mapping checkers to CLI invocations
- `batou_type.core.BASEDPYRIGHT_NOISE_RULES` — source: [src/batou_type/core.py:115](src/batou_type/core.py#L115) — `frozenset` of diagnostic rules filtered from basedpyright output
- `batou_type.core._filter_basedpyright_json` — source: [src/batou_type/core.py:124](src/batou_type/core.py#L124) — private function, filters basedpyright JSON
- `batou_type.cli.app` — source: [src/batou_type/cli.py:15](src/batou_type/cli.py#L15) — the Typer app instance
- `batou_type.cli.STUB_PACKAGES` — source: [src/batou_type/cli.py:21](src/batou_type/cli.py#L21) — `["batou-stubs", "batou_ext-stubs"]`
- `batou_type.cli.StubInfo` — source: [src/batou_type/cli.py:25](src/batou_type/cli.py#L25) — dataclass for stub version metadata
- `batou_type.cli.get_stub_versions` — source: [src/batou_type/cli.py:33](src/batou_type/cli.py#L33) — collects version/path for stub packages
- `batou_type.cli._run_check` — source: [src/batou_type/cli.py:59](src/batou_type/cli.py#L59) — shared logic between `check` command and potential future commands
- `batou_type.pytest_plugin.BatouComponentFile` — source: [src/batou_type/pytest_plugin.py:66](src/batou_type/pytest_plugin.py#L66) — `pytest.File` subclass
- `batou_type.pytest_plugin.BatouComponentItem` — source: [src/batou_type/pytest_plugin.py:73](src/batou_type/pytest_plugin.py#L73) — `pytest.Item` subclass

## Documented Features

- **Default checker is ty** — claimed in: [README.md:10](README.md#L10), [src/batou_type/core.py:53](src/batou_type/core.py#L53), [src/batou_type/cli.py:74](src/batou_type/cli.py#L74) — tested by: [tests/test_refactor_contract.py:169](tests/test_refactor_contract.py#L169) (`assert Checker.ty.value == "ty"`)
- **Multiple checkers via `-c` flag** — claimed in: [README.md:11-13](README.md#L11) — tested by: no dedicated test found
- **Component discovery via `components/**/*.py` glob** — claimed in: [README.md:5](README.md#L5), [README.md:49-51](README.md#L49) — tested by: [tests/test_refactor_contract.py:159](tests/test_refactor_contract.py#L159) (imports `find_components`)
- **Exit code 0 (no errors) / 1 (errors)** — claimed in: [README.md:27](README.md#L27) — tested by: no dedicated test found
- **Exit code 0 when no component files found** — claimed in: [README.md:63](README.md#L63) — tested by: no dedicated test found
- **basedpyright noise filtering** — claimed in: [README.md:35](README.md#L35) — tested by: no dedicated test found
- **mypy flags** (`--explicit-package-bases --check-untyped-defs --no-incremental`) — claimed in: [README.md:34](README.md#L34) — tested by: no dedicated test found
- **Status to stderr, checker output to stdout** — claimed in: [README.md:18-19](README.md#L18) — tested by: no dedicated test found
- **Migration testing workflow** — claimed in: [README.md:39-47](README.md#L39) — tested by: N/A (documentation/workflow claim)
- **`python -m batou_type` support** — implied by `__main__.py` — tested by: no dedicated test found
- **pytest plugin `--batou-ty` flag** — claimed in: source code [src/batou_type/pytest_plugin.py:16](src/batou_type/pytest_plugin.py#L16) — tested by: no dedicated test found
- **pytest `batou_ty` marker** — claimed in: source code [src/batou_type/pytest_plugin.py:24](src/batou_type/pytest_plugin.py#L24) — tested by: no dedicated test found
- **Version command shows stub package info** — claimed in: source code [src/batou_type/cli.py:49](src/batou_type/cli.py#L49) — tested by: no dedicated test found
- **Stubs table shown before checking** — claimed in: source code [src/batou_type/cli.py:62](src/batou_type/cli.py#L62) — tested by: no dedicated test found

## Configuration Surface

### pyproject.toml

| Section | Key | Value |
|---|---|---|
| `[build-system]` | `build-backend` | `hatchling.build` |
| `[build-system]` | `requires` | `hatchling>=1.27` |
| `[project]` | `name` | `batou-type` |
| `[project]` | `version` | `2.8.0.dev0` |
| `[project]` | `description` | `Type-check batou deployments` |
| `[project]` | `requires-python` | `>=3.10` |
| `[project]` | `dependencies` | `batou-stubs`, `batou_ext-stubs`, `basedpyright`, `mypy`, `pytest`, `rich`, `ty`, `typer` |
| `[project.scripts]` | `batou-type` | `batou_type.cli:app` |
| `[project.entry-points.pytest11]` | `batou_type` | `batou_type.pytest_plugin` |
| `[tool.hatch.build.targets.wheel]` | `packages` | `["src/batou_type"]` |
| `[tool.hatch.build.targets.sdist]` | `include` | `["src/batou_type"]` |
| `[tool.uv.sources]` | `batou-stubs` | `{ path = "../batou/stubs" }` |
| `[tool.uv.sources]` | `batou-ext-stubs` | `{ path = "../batou_ext/stubs" }` |
| `[dependency-groups]` | `dev` | `batou-ext-stubs`, `batou-stubs` |

### pyrightconfig.json

| Key | Value |
|---|---|
| `pythonVersion` | `"3.14"` |
| `typeCheckingMode` | `"strict"` |
| `reportExplicitAny` | `"none"` |
| `reportAny` | `"none"` |
| `reportMissingTypeStubs` | `true` |
| `reportImplicitOverride` | `"none"` |
| `reportInvalidTypeArguments` | `"none"` |
| `reportIncompatibleMethodOverride` | `"none"` |
| `reportIncompatibleVariableOverride` | `"none"` |
| `reportOverlappingOverload` | `"none"` |
| `reportAttributeAccessIssue` | `"none"` |

### Missing tool configs (no sections defined)

- `[tool.ruff]` — no ruff configuration in pyproject.toml, no `.ruff.toml`
- `[tool.pytest]` — no pytest configuration in pyproject.toml, no `conftest.py`, no `pytest.ini`
- `[tool.mypy]` — no mypy configuration in pyproject.toml
- `[tool.ty]` — no ty configuration in pyproject.toml

## Discrepancies / Audit Notes

1. **CLI name mismatch**: README consistently uses `batou-typecheck` but the actual console script is `batou-type`. The README never mentions the actual command name.
2. **No default command**: The README shows bare `batou-typecheck` (no subcommand) as valid usage, but the Typer app has `no_args_is_help=True` and requires an explicit subcommand. The `check` subcommand must be invoked explicitly.
3. **README missing `version` subcommand**: The `version` subcommand exists in the CLI but is not documented in the README.
4. **README missing pytest plugin**: The pytest plugin (`--batou-ty`, `batou_ty` marker) is not documented in the README.
5. **Stale .gitignore**: `.gitignore` references `src/batou_typecheck/` (old package name?) instead of `src/batou_type/`.
6. **No dedicated functional tests**: The only test file (`test_refactor_contract.py`) tests structural/architectural contracts, not functional behavior. No tests for actual type-checking, exit codes, output format, or checker filtering.
