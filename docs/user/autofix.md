# Autofix

`batou-type` fixes two recurring classes of type-check diagnostics automatically.

**Missing submodule imports** (`possibly-missing-submodule`): inserts `from batou_ext.X import Y` for accessed but unimported modules.

**`self._` dereferencing** (`unresolved-attribute`): transforms `self += X` to `self += (_ := X)` where `self._` is referenced in the same scope, then replaces `self._` with `_`.

Example transformation:

```diff
--- a/components/database/component.py
+++ b/components/database/component.py
@@ -1,4 +1,4 @@
 class Database(Component):
     def configure(self):
-        self += PostgreSQL(port=5432)
-        self._.port = 5432
+        self += (_ := PostgreSQL(port=5432))
+        _.port = 5432
```

## Preview fixes

```{code-block} shell
$ batou-type check --diff
```

Prints a unified diff with `a/` and `b/` file prefixes, syntax-highlighted:

```diff
--- a/components/app/component.py
+++ b/components/app/component.py
@@ -1,3 +1,4 @@
+from batou_ext.ssl import SSL
 class App(Component):
     def configure(self):
         self += SSL(hostname=self.hostname)
```

Summary line after the diff:

```{code-block} text
1 fixable file(s) (run without --diff to apply)
```

Exit code 1 when diffs exist, 0 when clean.

## Apply fixes

```{code-block} shell
$ batou-type check --fix
```

Writes modified files in-place.

## Verify fixes before writing

```{code-block} shell
$ batou-type check --fix --virtual
```

Copies component files into a temporary directory, applies fixes there, and runs a full type-check on the copies. If the fix does not reduce the total error count, the tool prints:

```{code-block} text
Fix did not reduce errors, skipping
```

The fix is discarded and the command exits with code 1. This catches cases where an autofix transformation is syntactically valid but introduces new type errors.

Use `--virtual` in CI pipelines for safety.

## Suppress the error report

```{code-block} shell
$ batou-type check --fix-only
```

Applies fixes but hides the per-component error report. Useful when you only care about the fix output.

## Combine flags

```{code-block} shell
$ batou-type check --diff            # preview only
$ batou-type check --diff --virtual  # preview with tempdir safety
$ batou-type check --fix             # apply in-place
$ batou-type check --fix --virtual   # apply with tempdir safety
$ batou-type check --fix-only        # apply, hide error report
$ batou-type check --diff -c ty      # preview for ty only
$ batou-type check --fix -v          # apply with verbose output
```
