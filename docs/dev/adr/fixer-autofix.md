# Fixer Autofix Implementations

## Context

Two common batou type-check diagnostics have deterministic, safe automated fixes: missing submodule imports and self-dereferencing on `Component | None`. These fixes transform source code using libcst to preserve formatting and comments.

## Decisions

### add-missing-import-impl

#### Context

Type checkers emit `possibly-missing-submodule` when code references `batou_ext.ssl.Certificate` without a corresponding `from batou_ext.ssl import Certificate`. The module path and name must be extracted from the diagnostic message since the diagnostic model does not carry structured AST information.

#### Decision

The fixer handles `possibly-missing-submodule` diagnostics by extracting the module path from the diagnostic message using three regex patterns in priority order: (1) attribute-of-module pattern (`attribute "X" of module "Y.Z"`), (2) dotted-name-in-quotes pattern (`"batou_ext.ssl"`), (3) source-line fallback (parses the offending line from source). It uses libcst to parse the AST, collects existing from-imports, then either merges the new name into an existing from-import statement or inserts a new import after the last existing import block.

#### Alternatives

a. Use `ast` module instead of libcst — rejected because libcst preserves whitespace, comments, and formatting; `ast` loses all formatting information when round-tripping.
b. String-based regex replacement — rejected because it cannot reliably detect existing imports or merge names into multi-name import statements; would break on edge cases like inline comments.

#### Consequences

The fixer is conservative: if regex extraction fails to find a module/name pair, or if libcst cannot parse the source, it returns `None` (no change). The three-pattern fallback ensures coverage across different checker output formats. Only truly new imports are inserted — if the name already exists in a from-import, no change is made.

### self-deref-impl

#### Context

In batou, `self +=` statements can create components whose attributes are accessed via `self._`. Type checkers see `self._` as accessing `Component | None` and flag it as an unresolved attribute. The fix uses the walrus operator to capture the added component and replace `self._` with the captured variable.

#### Context

The fixer handles `unresolved-attribute` diagnostics on `self._` references with a two-pass libcst transformation. Pass 1 (`_SelfDerefAnalyzer`, a `CSTVisitor`) scans for `self._` references within function scope to determine which `self +=` statements need walrus wrapping. Pass 2 (`_SelfDerefTransformer`, a `CSTTransformer`) applies the transformation selectively — only where `self._` is referenced between a `self +=` and the next `self +=` or end of function. It transforms `self += X` to `self += (_ := X)` and replaces `self._` with `_`.

#### Alternatives

a. Single-pass transformation that wraps every `self +=` — rejected because it would add unnecessary walrus operators to `self +=` statements that are never dereferenced, producing noisy diffs.
b. Text-based find-and-replace — rejected because it cannot track function scope boundaries and would incorrectly transform `self._` across different functions or in non-component contexts.

#### Consequences

The two-pass approach ensures minimal transformation: only `self +=` statements that actually have a corresponding `self._` reference in scope get the walrus operator. The analysis is scope-aware (per-function) so transformations in one function do not affect another. A quick `self._` pre-check on the raw source string avoids unnecessary libcst parsing when the pattern is absent.

## Verified By

- `tests/test_fixer.py::test_add_missing_import_inserts_new_import` — verifies new from-import insertion
- `tests/test_fixer.py::test_add_missing_import_merges_into_existing` — verifies merge into existing import
- `tests/test_fixer.py::test_add_missing_import_returns_none_when_already_present` — verifies no-op when import exists
- `tests/test_fixer.py::test_add_missing_import_invalid_python_returns_none` — verifies graceful failure on parse errors
- `tests/test_fixer.py::test_self_deref_walrus_when_deref_follows_augassign` — verifies walrus + replacement
- `tests/test_fixer.py::test_self_deref_no_transform_without_deref` — verifies no-op when no `self._` follows
- `tests/test_fixer.py::test_self_deref_selective_walrus_for_multiple_augassigns` — verifies selective transformation
- `tests/test_fixer.py::test_self_deref_no_self_underscore_in_source_returns_none` — verifies early exit
- `tests/impl_spec/test_autofix_missing_imports.py::TestAddMissingImportFixer` — contract tests for import insertion, merge, and positioning
- `tests/impl_spec/test_autofix_missing_imports.py::TestSelfDerefFixer` — contract tests for walrus wrap, replacement, no-op, and chained access
