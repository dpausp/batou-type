# Fixer Layer Architecture

## Context

The autofix feature required a new module for AST-based source transformations that fits into the existing four-layer architecture without pulling framework dependencies into lower layers.

## Decisions

### module-placement

#### Context

The fixer needs access to `Diagnostic` objects from `output.py` and uses `libcst` for AST manipulation. It must be callable from `cli.py` but must not depend on CLI frameworks (typer, rich, stogger) or testing infrastructure (pytest).

#### Decision

`fixer.py` is a new module placed between `cli.py` and `output.py` in the dependency graph. It imports only `Diagnostic` from `output.py` and `libcst`. It must not import from `cli.py`, `core.py`, or `pytest_plugin.py`. Dependency chain: `cli.py` → `fixer.py` → `output.py`.

#### Alternatives

a. Place fixer logic inside `cli.py` — rejected because it would couple AST transformation to CLI presentation, making the fixer untestable in isolation and violating framework isolation.
b. Place fixer logic inside `output.py` — rejected because `output.py` owns Pydantic modeling and JSON serialization; adding libcst there would mix two framework concerns (pydantic + libcst) in one module.

#### Consequences

The fixer is independently testable with just source strings and `Diagnostic` objects. Adding new fixers requires no changes to `cli.py` beyond registering the instance. The architecture enforces a strict one-directional dependency flow.

### fixer-protocol

#### Context

Multiple autofix transformations share the same interface: claim diagnostics by error code, receive source code, return transformed source. A uniform protocol enables the CLI to route diagnostics to the correct fixer without knowing implementation details.

#### Decision

`Fixer` is a `@dataclass(slots=True)` with fields `slug` (str), `diagnostic_codes` (`frozenset[str]`), and method `apply(self, source: str, diagnostics: list[Diagnostic]) -> str | None`. Returns `None` if nothing changed.

#### Alternatives

a. Abstract base class with abstract `apply` — rejected because the dispatch logic is slug-based (`match` on `self.slug`), not polymorphic; a dataclass is simpler and sufficient.
b. Plain functions with a registry dict — rejected because a dataclass encapsulates the code-to-fixer mapping (`diagnostic_codes`) alongside the transformation logic, keeping related state together.

#### Consequences

Each fixer is self-describing: its `diagnostic_codes` declares what it handles. The `apply` return contract (`str | None`) makes it easy to chain fixers and detect whether any transformation occurred.

### diagnostic-matching

#### Context

The CLI needs to route each diagnostic to exactly one fixer. Ambiguous routing (two fixers handling the same code) would cause unpredictable behavior when both try to modify the same source.

#### Decision

Each fixer instance declares `diagnostic_codes` as a `frozenset[str]`. Routing is deterministic: one code maps to exactly one fixer. The two registered instances have disjoint codesets: `possibly-missing-submodule` → `ADD_MISSING_IMPORT`, `unresolved-attribute` → `SELF_DEREF`.

#### Alternatives

a. Allow overlapping codes with priority ordering — rejected because it introduces ordering complexity and makes it hard to predict which fixer runs first on the same diagnostic.
b. Single fixer handles all codes with internal branching — rejected because it creates a monolithic function; disjoint codesets enforce separation of concerns per fixer instance.

#### Consequences

Adding a new fixer requires only creating a new `Fixer` instance with a unique codeset and adding it to the fixers list in `run_fix()`. The disjoint codeset constraint is enforced by convention and verified by the `diagnostic_codes` being `frozenset` (immutable after creation).

## Verified By

- `tests/test_architecture.py::TestFixerLayer` — enforces fixer.py imports only from `output.py`, bans typer, rich, pytest, structlog, stogger, cli, and pytest_plugin
- `tests/test_architecture.py::TestCrossLayerIsolation::test_cli_may_import_fixer` — enforces cli.py → fixer.py dependency direction
- `tests/impl_spec/test_autofix_missing_imports.py::TestFixerModule` — verifies Fixer dataclass fields, registered instances, and `apply` protocol
- `tests/impl_spec/test_autofix_missing_imports.py::TestFixerArchitecture` — enforces fixer.py layer constraints via pytest-archon
- `tests/impl_spec/test_autofix_missing_imports.py::TestLibcstDependency` — verifies libcst is a declared project dependency
