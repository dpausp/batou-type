# Setup Command Pipeline

## Context

batou-type wraps type checking for batou deployment projects. Users needed a way to configure their projects so that `ty check`, `mypy`, and `pyright` work natively without the batou-type wrapper, enabling IDE integration via LSP.

## Decisions

### stub-source

#### Context

`batou-stubs` and `batou_ext-stubs` are not published on PyPI. They exist only as vendored stubs inside batou-type's `src/batou_type/vendor/` directory.

#### Decision

Copy vendored stubs from batou-type's `vendor/` into the target project as `stubs/batou/` and `stubs/batou_ext/`. These are PEP 561 stub packages. Checker configs reference `stubs/` via search-path settings.

#### Alternatives

a. Editable pip install of vendor/ — breaks when batou-type is uninstalled.
b. Publish stubs on PyPI first — larger scope, separate work item.

#### Consequences

No network access required. Stubs are pinned to the batou-type version that ran setup. Updating requires re-running `batou-type setup` (idempotent).

### module-placement

#### Context

`setup.py` must fit the existing four-layer architecture without violating dependency rules. It handles filesystem operations and TOML manipulation.

#### Decision

New module `src/batou_type/setup.py`. Architecture rules enforced by pytest-archon: no typer/rich/pytest/pydantic/libcst imports, no `batou_type` imports. `cli.py` imports from `setup.py`; `setup.py` has no upward dependencies.

#### Consequences

`cli.py` gains an import from `setup.py`. The layer diagram gains a new entry between the CLI and core layers.

### pyproject-write

#### Context

Setup reads and writes `pyproject.toml`. Python 3.13 provides `tomllib` (read-only). Writing requires a separate library.

#### Decision

Add `tomli-w` as a production dependency. Read with `tomllib`, write with `tomli_w`. Correct TOML roundtripping preserves existing content.

#### Consequences

One new production dependency. Setup reads existing `pyproject.toml` into a dict, adds checker sections, writes back.

### checker-install

#### Context

Setup writes checker configuration. Whether it also installs type checkers (ty, mypy, pyright) is a scope question.

#### Decision

Config only — does NOT install type checkers. Zero package installation logic. No uv/pip subprocess calls.

#### Consequences

Setup works without uv in PATH. Cleaner separation: setup = configuration, package management = user responsibility.

### existing-config

#### Context

A project may already have `[tool.ty]`, `[tool.mypy]`, or `[tool.pyright]` sections.

#### Decision

If any target section already exists without the setup marker, abort with error listing conflicting sections. If sections exist with the marker (from a previous setup run), overwrite them (idempotent).

#### Alternatives

a. Merge — risk of corrupting hand-tuned config.

#### Consequences

Setup is safe — never silently modifies existing checker config. Error message suggests manual integration.

### idempotency

#### Context

Users may run setup multiple times.

#### Decision

Idempotent. Comment marker `# managed by batou-type setup` identifies setup-managed sections. On re-run: overwrite marked sections, abort on unmarked existing sections.

#### Alternatives

a. Guard file — hidden state, unclear lifecycle.
b. Always overwrite — loses manual config.

#### Consequences

Safe re-runs. User can distinguish setup-managed from hand-tuned config in `pyproject.toml`.

## Verified By

